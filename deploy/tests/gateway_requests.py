"""Executed via stdin in a disposable client container by gateway_smoke.py."""
import io
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from PIL import Image


def request(path, method='GET', body=None, headers=None):
    req = Request('http://nginx:8080' + path, data=body, method=method, headers=headers or {})
    try:
        response = urlopen(req, timeout=20)
    except HTTPError as error:
        response = error
    return response.status, response.headers, response.read()


def api(path, method='GET', payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    status, headers, body = request('/api' + path, method, json.dumps(payload).encode() if payload is not None else None, headers)
    return status, json.loads(body)


for path in ('/', '/events', '/admin', '/admin/login', '/api/health', '/robots.txt'):
    assert request(path)[0] == 200, 'Route failed: ' + path
assert request('/sitemap.xml')[0] == 503  # SITE_URL deliberately unset locally.
public_html = request('/events')[2].decode()
next_asset = re.search(r'src="(/_next/[^\"]+\.js[^\"]*)"', public_html)
assert next_asset and request(next_asset[1])[0] == 200
login_html = request('/admin/login')[2].decode()
assert 'admin123' not in login_html
asset = re.search(r'src="(/admin/static/[^\"]+\.js)"', login_html)
assert asset and request(asset[1])[0] == 200
assert 'immutable' in request(asset[1])[1].get('Cache-Control', '')
stylesheet = re.search(r'href="(/admin/static/[^\"]+\.css)"', login_html)
assert stylesheet and request(stylesheet[1])[0] == 200
assert request('/admin/login')[1].get('Cache-Control') == 'no-store'
assert b'afisha.lalexonl.ru' not in request(asset[1])[2]
assert request('/admin/static/missing.js')[0] == 404
assert request('/admin/login')[2] == request('/admin/login')[2]  # Direct refresh.
assert request('/static/uploads/.env')[0] == 404
assert request('/api/admin/events/')[0] in (401, 403)
assert request('/api/health')[2] == b'{"status":"healthy"}'
assert request('/api/health')[1].get('X-Powered-By') is None
assert request('/api/health')[1].get('Cache-Control') == 'no-store'

status, login = request('/api/auth/login', 'POST', urlencode(TEST_LOGIN).encode(), {'Content-Type':'application/x-www-form-urlencoded'})[::2]
assert status == 200
token = json.loads(login)['access_token']
assert api('/auth/me', token=token)[0] == 200
status, category = api('/categories/', 'POST', {'name':'Gateway category','slug':'gateway'}, token)
assert status == 200
buffer = io.BytesIO()
Image.new('RGB', (8,8), 'green').save(buffer, format='PNG')
image = buffer.getvalue()
boundary = 'gateway-test-boundary'
multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
             + image + f'\r\n--{boundary}--\r\n'.encode())
status, _, body = request('/api/events/upload-image', 'POST', multipart,
                          {'Authorization':'Bearer '+token,'Content-Type':'multipart/form-data; boundary='+boundary})
assert status == 200
image_url = json.loads(body)['image_url']
status, headers, loaded = request(image_url)
assert status == 200 and headers.get('X-Content-Type-Options') == 'nosniff'
# Upload validation intentionally re-encodes PNG as RGBA. Verify the decoded
# image rather than requiring byte identity with the untrusted input.
with Image.open(io.BytesIO(loaded)) as decoded:
    assert decoded.size == (8, 8) and decoded.convert('RGB').getpixel((0, 0)) == (0, 128, 0)
status, _, _ = request('/api/events/upload-image', 'POST', b'x'*(6*1024*1024+1), {'Authorization':'Bearer '+token})
assert status == 413
status, event = api('/events/', 'POST', {
    'title':'Gateway event', 'datetime':'2099-12-15T12:00:00', 'location':'Test location',
    'image_url':image_url,'category_id':category['id'],'organizer_id':1,
    'event_url':'https://example.invalid/register','source':'https://example.invalid/source'}, token)
assert status == 200
identifier = event['id']
assert request('/events/'+str(identifier))[0] == 404
assert api('/admin/events/', token=token)[1]['total_items'] == 1
assert api(f'/admin/events/{identifier}/verify', 'POST', token=token)[0] == 200
assert api(f'/admin/events/{identifier}/publication', 'PATCH', {'publication_status':'published'}, token)[0] == 200
assert request('/events/'+str(identifier))[0] == 200
assert api('/events/?date=2099-12-15&category=gateway&page=1&limit=1')[1]['total_items'] == 1
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None

try:
    build_opener(NoRedirect).open('http://nginx:8080/api/events?limit=1')
except HTTPError as error:
    assert error.code == 307
    assert '/api/events/?limit=1' in error.headers['Location']
else:
    raise AssertionError('Expected FastAPI slash redirect')
assert api(f'/events/{identifier}', 'PUT', {'description':'Updated'}, token)[0] == 200
assert api(f'/admin/events/{identifier}/publication', 'PATCH', {'publication_status':'draft'}, token)[0] == 200
assert request('/events/'+str(identifier))[0] == 404
assert api(f'/admin/events/{identifier}/status', 'PATCH', {'event_status':'cancelled'}, token)[0] == 200
assert api(f'/admin/events/{identifier}/verify', 'POST', token=token)[0] == 200
assert api(f'/admin/events/{identifier}/publication', 'PATCH', {'publication_status':'published'}, token)[0] == 200
assert request('/events/'+str(identifier))[0] == 200

for attempt in range(4):
    status, headers, _ = request('/api/auth/login','POST',f'username=source-{attempt}&password=wrong'.encode(), {
        'Content-Type':'application/x-www-form-urlencoded','X-Forwarded-For':f'198.51.100.{attempt}',
        'Forwarded':f'for=203.0.113.{attempt}','X-Real-IP':f'192.0.2.{attempt}'})
    assert status == (401 if attempt < 3 else 429), 'Spoofed forwarding bypassed source limit'
assert int(headers['Retry-After']) > 0
