"""No external requests: resolver/transport are controlled fixtures."""
from datetime import timedelta
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.imports.fetcher import SafeFetcher, resolve_public, pinned_request, MAX_BYTES
from app.imports.jsonld import extract
from app.imports.policy import ImportFailure, safe_url, check_policy
from app.imports.worker import now

@pytest.fixture
def source():
    return SimpleNamespace(state='enabled',access_method='jsonld_html',adapter_key='jsonld_html',
        permission_basis='written_permission',permission_reference='fixture',terms_url='https://example.invalid/terms',
        terms_checked_by=1,terms_checked_at=now()-timedelta(days=1),review_due_at=now()+timedelta(days=1),
        blocked_until=None,allowed_origins=['https://example.invalid'],allowed_path_prefixes=['/events'],request_interval_seconds=1)

@pytest.mark.parametrize('url',['file:///etc/passwd','https://user:pass@example.invalid/events','https://example.invalid/a/../events',
    'https://example.invalid/events%2f..','https://example.invalid//events','https://example.invalid/events?token=secret',
    'https://example.invalid/events?api_key=secret','https://example.invalid/\\events','https://example.invalid:bad/events'])
def test_ambiguous_secret_urls(url):
    with pytest.raises(ImportFailure): safe_url(url)


def test_identity_keeps_meaningful_query():
    assert safe_url('HTTPS://EXAMPLE.invalid:443/events?id=4&utm_source=test#preview')=='https://example.invalid/events?id=4'
    assert safe_url('https://example.invalid/events?id=5')!='https://example.invalid/events?id=4'


@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','172.16.0.1','192.168.1.1','169.254.169.254','0.0.0.0','::1','fc00::1','fe80::1','::ffff:8.8.8.8','2002:0808:0808::1','224.0.0.1'])
def test_dns_forbidden_addresses(monkeypatch,ip):
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**k:[(2,1,6,'',(ip,443)),(2,1,6,'',('8.8.8.8',443))])
    with pytest.raises(ImportFailure,match='unsafe_address'): resolve_public('example.invalid',443)


def test_dns_pinning_connects_ip_not_name(monkeypatch):
    sock=Mock(); sock.getpeername.return_value=('8.8.8.8',443)
    connect=Mock(return_value=sock); monkeypatch.setattr('socket.create_connection',connect)
    context=Mock(); context.wrap_socket.return_value=sock
    monkeypatch.setattr('ssl.create_default_context',lambda:context)
    conn=Mock(); response=conn.getresponse.return_value
    response.status=200; response.getheaders.return_value=[('content-type','text/html')]; response.read1.side_effect=[b'OK',b'']
    monkeypatch.setattr('http.client.HTTPConnection',lambda *a,**k:conn)
    status,_,body=pinned_request('https://example.invalid/events','8.8.8.8')
    assert status==200 and body==b'OK'
    connect.assert_called_once_with(('8.8.8.8',443),timeout=8)
    context.wrap_socket.assert_called_once_with(sock,server_hostname='example.invalid',do_handshake_on_connect=False)
    sock.do_handshake.assert_called_once()


@pytest.mark.parametrize('location',['http://example.invalid/events','https://127.0.0.1/events','https://other.invalid/events','https://example.invalid/private'])
def test_redirect_fail_closed(source,location):
    transport=Mock(return_value=(302,{'location':location},b''))
    f=SafeFetcher(source,lambda:None,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
    with pytest.raises(ImportFailure): f.get('https://example.invalid/events')
    assert transport.call_count==1


def test_rebinding_each_redirect_is_checked(source,monkeypatch):
    answers=iter(['8.8.8.8','127.0.0.1'])
    monkeypatch.setattr('socket.getaddrinfo',lambda *a,**k:[(2,1,6,'',(next(answers),443))])
    transport=Mock(return_value=(302,{'location':'/events/next'},b''))
    f=SafeFetcher(source,lambda:None,transport=transport)
    with pytest.raises(ImportFailure,match='unsafe_address'): f.get('https://example.invalid/events')
    assert transport.call_count==1


@pytest.mark.parametrize('status',[403,429])
def test_forbidden_stops_no_retry(source,status):
    transport=Mock(return_value=(status,{},b''))
    f=SafeFetcher(source,lambda:None,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
    with pytest.raises(ImportFailure,match=f'http_{status}'): f.get('https://example.invalid/events')
    assert transport.call_count==1


def test_limits_robots_and_origin(source):
    for url,allowed in [('https://else.invalid/events',None),('https://example.invalid/private',None),('https://example.invalid/events',lambda _:False)]:
        transport=Mock()
        f=SafeFetcher(source,lambda:None,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
        with pytest.raises(ImportFailure): f.get(url,allowed=allowed)
        transport.assert_not_called()
    f=SafeFetcher(source,lambda:None,resolver=lambda *a,**k:['8.8.8.8'],transport=lambda *a,**k:(200,{},b'x'*(MAX_BYTES+1)))
    with pytest.raises(ImportFailure,match='response_too_large'): f.get('https://example.invalid/events')


@pytest.mark.parametrize('date',['2026-11-23T18:00:00','2026-11-23','9999-12-31T00:00:00Z','bad'])
def test_ambiguous_time_never_assumed(date):
    records=extract(json.dumps({'@type':'Event','name':'Fact','startDate':date}).encode(),'application/ld+json','https://example.invalid/events')
    assert records[0]['facts']['start_at'] is None and records[0]['facts']['time_resolution']=='ambiguous'


def test_graph_array_html_no_copyright_copy():
    raw={'@graph':[{'@type':['Thing','Event'],'name':'Fact','startDate':'2026-11-23T18:00:00+07:00',
        'description':'PROTECTED','image':'PROTECTED','organizer':{'email':'PROTECTED'}}]}
    body=('<script type="application/ld+json">'+json.dumps(raw)+'</script>').encode()
    records=extract(body,'text/html','https://example.invalid/events')
    assert len(records)==1 and 'PROTECTED' not in str(records)
    assert records[0]['facts']['start_at'].hour==11
    with pytest.raises(ImportFailure): extract(b'<html>none</html>','text/html','https://example.invalid/events')


@pytest.mark.parametrize('field,value',[('state','prohibited'),('access_method','manual_only'),('permission_basis',None),('review_due_at',now()-timedelta(days=1))])
def test_permission_fail_closed(source,field,value):
    setattr(source,field,value)
    with pytest.raises(ImportFailure): check_policy(source)


def test_robots_redirect_cannot_fetch_other_paths(source):
    transport=Mock(return_value=(302,{'location':'/events'},b''))
    f=SafeFetcher(source,lambda:None,resolver=lambda *a,**k:['8.8.8.8'],transport=transport)
    with pytest.raises(ImportFailure,match='unsafe_robots_redirect'):
        f.get('https://example.invalid/robots.txt',robots=True)
    assert transport.call_count==1


def test_end_dates_schedules_and_json_limits():
    raw={'@type':'Event','name':'Meeting','startDate':'2026-11-23T18:00:00+07:00','endDate':'2026-11-23T17:00:00+07:00'}
    facts=extract(json.dumps(raw).encode(),'application/ld+json','https://example.invalid/events')[0]['facts']
    assert facts['end_at'] is None and 'end_time_requires_review' in facts['warnings']
    raw['eventSchedule']={'repeatFrequency':'P1W'}
    assert extract(json.dumps(raw).encode(),'application/ld+json','https://example.invalid/events')[0]['facts']['start_at'] is None
    with pytest.raises(ImportFailure): extract(b'{' ,'application/ld+json','https://example.invalid/events')
    with pytest.raises(ImportFailure,match='record_limit'):
        extract(json.dumps([raw]*101).encode(),'application/ld+json','https://example.invalid/events')


def test_shared_dns_http_deadline_and_no_connect_after_expiry(source,monkeypatch):
    from app.imports import fetcher
    clock=[100.0]
    monkeypatch.setattr(fetcher.time,'monotonic',lambda:clock[0])
    def resolve(*args,deadline):
        assert deadline==120
        clock[0]+=4
        return ['8.8.8.8']
    def transport(url,ip,*,deadline):
        assert deadline==120 and fetcher.remaining(deadline)==16
        clock[0]=120
        return 200,{},b'late'
    with pytest.raises(ImportFailure,match='response_deadline'):
        SafeFetcher(source,lambda:None,resolver=resolve,transport=transport).get('https://example.invalid/events')
    clock[0]=100
    def expired(*args,**kwargs):
        clock[0]=121
        return ['8.8.8.8']
    transport=Mock()
    with pytest.raises(ImportFailure,match='response_deadline'):
        SafeFetcher(source,lambda:None,resolver=expired,transport=transport).get('https://example.invalid/events')
    transport.assert_not_called()


@pytest.mark.parametrize('phase',['headers','body'])
def test_absolute_deadline_interrupts_trickle_socket(monkeypatch,phase):
    import socket, threading, time
    from app.imports import fetcher
    client,server=socket.socketpair()
    wrapped=Mock(wraps=client);wrapped.getpeername.return_value=('8.8.8.8',80)
    monkeypatch.setattr(fetcher.socket,'create_connection',lambda *a,**k:wrapped)
    stop=threading.Event()
    def trickle():
        try:
            server.recv(8192)
            prefix=b'HTTP/1.1 200 OK\r\nX-Slow: ' if phase=='headers' else b'HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n'
            server.sendall(prefix)
            while not stop.wait(.01): server.sendall(b'x')
        except OSError: pass
        finally: server.close()
    thread=threading.Thread(target=trickle,daemon=True);thread.start();started=time.monotonic()
    try:
        with pytest.raises(ImportFailure,match='response_deadline'):
            pinned_request('http://example.invalid/events','8.8.8.8',deadline=started+.25)
        assert time.monotonic()-started<2
        if phase=='headers':
            wrapped.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        assert client.fileno()==-1
    finally:
        stop.set();client.close();thread.join(timeout=2)
    assert not thread.is_alive()


def test_connect_tls_share_remaining_budget(monkeypatch):
    from app.imports import fetcher
    clock=[100.0];monkeypatch.setattr(fetcher.time,'monotonic',lambda:clock[0])
    sock=Mock();sock.getpeername.return_value=('8.8.8.8',443)
    def connect(*args,**kwargs):
        assert kwargs['timeout']==3
        clock[0]=102
        return sock
    monkeypatch.setattr(fetcher.socket,'create_connection',connect)
    context=Mock();context.wrap_socket.return_value=sock
    monkeypatch.setattr(fetcher.ssl,'create_default_context',lambda:context)
    def handshake():
        assert sock.settimeout.call_args.args==(1.0,)
        clock[0]=104
    sock.do_handshake.side_effect=handshake
    with pytest.raises(ImportFailure,match='response_deadline'):
        pinned_request('https://example.invalid/events','8.8.8.8',deadline=103)
    sock.close.assert_called_once()


def test_network_budget_fits_lease():
    from app.imports.fetcher import REQUEST_DEADLINE_SECONDS
    from app.imports.worker import LEASE_SECONDS
    assert 0<REQUEST_DEADLINE_SECONDS<LEASE_SECONDS==45


def test_dns_wait_obeys_absolute_deadline_and_releases_slot(monkeypatch):
    import threading, time
    from app.imports import fetcher
    release=threading.Event();finished=threading.Event()
    def lookup(*a,**k):
        try:
            release.wait(timeout=2)
            return [(2,1,6,'',('8.8.8.8',443))]
        finally: finished.set()
    monkeypatch.setattr(fetcher.socket,'getaddrinfo',lookup)
    started=time.monotonic()
    try:
        with pytest.raises(ImportFailure,match='response_deadline'):
            resolve_public('example.invalid',443,deadline=started+.1)
        assert time.monotonic()-started<1
    finally:
        release.set();assert finished.wait(timeout=2)
