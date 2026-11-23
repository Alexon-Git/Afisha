"""Fail-closed source policy and unambiguous URL identities. No network here."""
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class ImportFailure(Exception):
    def __init__(self, code, *, blocked=False):
        super().__init__(code)
        self.code, self.blocked = code, blocked


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     default=str, separators=(',', ':')).encode()).hexdigest()


def safe_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\s\\\x00-\x1f\x7f]', value):
        raise ImportFailure('invalid_url', blocked=True)
    try:
        u = urlsplit(value)
        if u.scheme not in {'https', 'http'} or not u.hostname or u.username is not None or u.password is not None:
            raise ValueError()
        # Deliberately narrow generic adapter: no encoded/ambiguous paths or signed/query credentials.
        if '%' in u.path or '//' in u.path or any(x in {'.', '..'} for x in u.path.split('/')):
            raise ValueError()
        host = u.hostname.encode('idna').decode('ascii').lower()
        port = u.port
        if ':' in host:
            host = f'[{host}]'
        origin = f'{u.scheme}://{host}' + (f':{port}' if port and port != (443 if u.scheme == 'https' else 80) else '')
        query = parse_qsl(u.query, keep_blank_values=True, strict_parsing=False, max_num_fields=40)
        if any(re.search(r'token|secret|password|credential|signature|api.?key|authorization|session', k, re.I) for k, _ in query):
            raise ValueError()
        query = [(k,v) for k,v in query if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
        return urlunsplit((u.scheme, origin.split('://',1)[1], u.path or '/', urlencode(query), ''))
    except (ValueError, UnicodeError):
        raise ImportFailure('invalid_url', blocked=True) from None


def origin_of(url):
    u = urlsplit(safe_url(url))
    return f'{u.scheme}://{u.netloc}'


def check_policy(source, now=None):
    now = now or datetime.now(timezone.utc)
    if (source.state != 'enabled' or source.access_method != 'jsonld_html' or source.adapter_key != 'jsonld_html'
        or source.permission_basis not in {'published_terms','written_permission','api_agreement'}
        or not source.permission_reference or not source.terms_url or not source.terms_checked_by
        or not source.terms_checked_at or source.terms_checked_at > now
        or not source.review_due_at or source.review_due_at <= now
        or (source.blocked_until and source.blocked_until > now)
        or not source.allowed_origins or not source.allowed_path_prefixes):
        raise ImportFailure('source_not_authorized', blocked=True)
    if getattr(source, 'robots_state', 'unknown') == 'denied':
        raise ImportFailure('robots_disallowed', blocked=True)
    if source.request_interval_seconds < 1:
        raise ImportFailure('invalid_source_policy', blocked=True)


def check_url(source, url, *, robots=False):
    url = safe_url(url)
    u = urlsplit(url)
    if origin_of(url) not in source.allowed_origins:
        raise ImportFailure('origin_not_allowed', blocked=True)
    if not robots and not any((u.path == prefix.rstrip('/') or u.path.startswith(prefix.rstrip('/') + '/'))
                              for prefix in source.allowed_path_prefixes if isinstance(prefix,str) and prefix.startswith('/')):
        raise ImportFailure('path_not_allowed', blocked=True)
    return url
