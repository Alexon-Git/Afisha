"""Bounded HTTPS/HTTP transport: validated DNS address is the connected address.

No environment proxies, cookies, auth, compression, JavaScript or retry bypasses.
TLS still verifies the original hostname with SNI after IP pinning.
"""
import http.client
import ipaddress
import socket
import ssl
import time
import threading
from queue import Queue, Empty
from urllib.parse import urljoin, urlsplit

from .policy import ImportFailure, check_url

MAX_BYTES = 1_048_576
TIMEOUT = 8
REQUEST_DEADLINE_SECONDS = 20  # DNS through body, below the 45-second lease.
MAX_REQUESTS = 8
USER_AGENT = 'AfishaImport/1.0'


_DNS_SLOTS = threading.BoundedSemaphore(4)


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise ImportFailure('response_deadline')
    return value


def resolve_public(host, port, *, deadline=None):
    # getaddrinfo has no portable timeout. Bound concurrent daemon resolvers and
    # the caller's wait; stuck DNS cannot grow threads/queues or block shutdown.
    deadline = deadline if deadline is not None else time.monotonic() + REQUEST_DEADLINE_SECONDS
    remaining(deadline)
    if not _DNS_SLOTS.acquire(blocking=False):
        raise ImportFailure('dns_failure')
    result = Queue(maxsize=1)
    def lookup():
        try:
            result.put(socket.getaddrinfo(host,port,type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)
        finally:
            _DNS_SLOTS.release()
    threading.Thread(target=lookup,daemon=True).start()
    try:
        rows = result.get(timeout=min(5, remaining(deadline)))
    except Empty:
        remaining(deadline)
        raise ImportFailure('dns_failure') from None
    remaining(deadline)
    answers = {item[4][0] for item in rows} if rows else set()
    if not answers:
        raise ImportFailure('dns_failure')
    for value in answers:
        address = ipaddress.ip_address(value)
        if (not address.is_global or address.is_multicast or address.is_unspecified
            or getattr(address, 'ipv4_mapped', None) is not None
            or getattr(address, 'sixtofour', None) is not None
            or getattr(address, 'teredo', None) is not None
            or (address.version == 6 and address in ipaddress.ip_network('64:ff9b::/96'))):
            raise ImportFailure('unsafe_address', blocked=True)
    return sorted(answers)


def pinned_request(url, ip, *, deadline=None):
    """Return status, selected headers, bounded bytes. Never resolve host again."""
    u = urlsplit(url)
    port = u.port or (443 if u.scheme == 'https' else 80)
    conn = http.client.HTTPConnection(u.hostname, port, timeout=TIMEOUT)
    sock = None
    deadline = deadline if deadline is not None else time.monotonic() + REQUEST_DEADLINE_SECONDS
    expired = threading.Event()
    sockets = []
    def abort():
        expired.set()
        # shutdown interrupts recv even when HTTPResponse holds a makefile ref.
        # A socket timeout alone permits an endless trickle of header bytes.
        for active in tuple(sockets):
            try:
                active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                active.close()
            except OSError:
                pass
    watchdog = threading.Timer(remaining(deadline), abort)
    watchdog.daemon = True
    watchdog.start()
    try:
        sock = socket.create_connection((ip, port), timeout=min(TIMEOUT, remaining(deadline)))
        sockets.append(sock)
        remaining(deadline)
        if ipaddress.ip_address(sock.getpeername()[0]) != ipaddress.ip_address(ip):
            raise ImportFailure('peer_mismatch', blocked=True)
        sock.settimeout(min(TIMEOUT, remaining(deadline)))
        if u.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(
                sock, server_hostname=u.hostname, do_handshake_on_connect=False)
            sockets.append(sock)
            sock.settimeout(min(TIMEOUT, remaining(deadline)))
            sock.do_handshake()
        remaining(deadline)
        conn.sock = sock
        path = u.path or '/'
        if u.query:
            path += '?' + u.query
        conn.request('GET', path, headers={'User-Agent':USER_AGENT, 'Accept':'text/html, application/ld+json, text/plain',
                                          'Accept-Encoding':'identity', 'Connection':'close'})
        remaining(deadline)
        sock.settimeout(min(TIMEOUT, remaining(deadline)))
        response = conn.getresponse()
        remaining(deadline)
        headers = {k.lower():v for k,v in response.getheaders() if k.lower() in {'location','content-type','content-length','content-encoding'}}
        if response.status in {403,429} or response.status in {301,302,303,307,308}:
            return response.status, headers, b''
        if headers.get('content-encoding','identity').lower() != 'identity':
            raise ImportFailure('compressed_response')
        if headers.get('content-length') and (not headers['content-length'].isdigit() or int(headers['content-length']) > MAX_BYTES):
            raise ImportFailure('response_too_large')
        chunks, size = [], 0
        while True:
            sock.settimeout(min(TIMEOUT, remaining(deadline)))
            chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
            remaining(deadline)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ImportFailure('response_too_large')
            chunks.append(chunk)
        return response.status, headers, b''.join(chunks)
    except ImportFailure:
        raise
    except (OSError, ValueError, http.client.HTTPException):
        if expired.is_set() or time.monotonic() >= deadline:
            raise ImportFailure('response_deadline') from None
        raise ImportFailure('network_failure') from None
    finally:
        watchdog.cancel()
        watchdog.join()
        conn.close()
        if sock:
            sock.close()


class SafeFetcher:
    def __init__(self, source, before_request, resolver=None, transport=None):
        self.source = source
        self.before_request = before_request
        self.resolver = resolver or resolve_public
        self.transport = transport or pinned_request
        self.requests = 0
        self.bytes = 0

    def get(self, url, *, robots=False, allowed=None):
        for hop in range(4):
            url = check_url(self.source, url, robots=robots)
            if allowed and not allowed(url):
                raise ImportFailure('robots_disallowed', blocked=True)
            if self.requests >= MAX_REQUESTS:
                raise ImportFailure('request_budget')
            self.before_request()
            self.requests += 1
            deadline = time.monotonic() + REQUEST_DEADLINE_SECONDS
            u = urlsplit(url)
            addresses = self.resolver(u.hostname, u.port or (443 if u.scheme == 'https' else 80), deadline=deadline)
            remaining(deadline)
            status, headers, body = self.transport(url, addresses[0], deadline=deadline)
            remaining(deadline)
            if len(body) > MAX_BYTES:
                raise ImportFailure('response_too_large')
            self.bytes += len(body)
            if status in {403,429}:
                raise ImportFailure(f'http_{status}', blocked=True)
            if status in {301,302,303,307,308}:
                target = urljoin(url, headers.get('location',''))
                if not headers.get('location') or (u.scheme == 'https' and urlsplit(target).scheme != 'https'):
                    raise ImportFailure('unsafe_redirect', blocked=True)
                if robots and (urlsplit(target).path != '/robots.txt' or urlsplit(target).query):
                    raise ImportFailure('unsafe_robots_redirect', blocked=True)
                # Robots redirects to another origin require separate rules: fail closed.
                if urlsplit(target).netloc != u.netloc:
                    raise ImportFailure('cross_origin_redirect', blocked=True)
                url = target
                continue
            if not 200 <= status < 300:
                raise ImportFailure('http_error')
            return url, headers, body
        raise ImportFailure('redirect_limit')
