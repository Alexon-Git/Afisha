import assert from 'node:assert/strict';
import { afterEach, test, mock } from 'node:test';
import { getBackendHealth, getPublishedEvents as serverEvents } from '../src/api/server.ts';
import { getPublishedEvents as browserEvents } from '../src/api/browser.ts';

const originalInternal = process.env.INTERNAL_API_URL;
const originalPublic = process.env.NEXT_PUBLIC_API_BASE;
afterEach(() => {
  mock.restoreAll();
  if (originalInternal === undefined) delete process.env.INTERNAL_API_URL;
  else process.env.INTERNAL_API_URL = originalInternal;
  if (originalPublic === undefined) delete process.env.NEXT_PUBLIC_API_BASE;
  else process.env.NEXT_PUBLIC_API_BASE = originalPublic;
});

test('server health uses only the internal URL with no credentials or caching', async () => {
  process.env.INTERNAL_API_URL = 'http://backend:8039';
  const fetch = mock.method(globalThis, 'fetch', async () => Response.json({ status: 'healthy' }));
  assert.deepEqual(await getBackendHealth(), { status: 'healthy' });
  const [url, options] = fetch.mock.calls[0].arguments;
  assert.equal(url, 'http://backend:8039/health');
  assert.equal(options?.credentials, 'omit');
  assert.equal(options?.cache, 'no-store');
  assert.equal(options?.redirect, 'error');
  assert.deepEqual(options?.headers, { Accept: 'application/json' });
});

test('server event client uses public events endpoint and preserves opaque legacy datetimes', async () => {
  process.env.INTERNAL_API_URL = 'http://backend:8039';
  const data = { items: [{ datetime: '2026-11-12T12:00:00' }], page: 2, limit: 10, total_items: 11, total_pages: 2 };
  const fetch = mock.method(globalThis, 'fetch', async () => Response.json(data));
  assert.deepEqual(await serverEvents(2), data);
  assert.equal(fetch.mock.calls[0].arguments[0], 'http://backend:8039/events/?page=2&limit=10');
});

test('browser events use only the same-origin public base', async () => {
  process.env.INTERNAL_API_URL = 'http://must-never-be-used:8039';
  process.env.NEXT_PUBLIC_API_BASE = '/api';
  const fetch = mock.method(globalThis, 'fetch', async () => Response.json({ items: [] }));
  await browserEvents();
  assert.equal(fetch.mock.calls[0].arguments[0], '/api/events/?page=1&limit=10');
});

test('external browser base is rejected before fetch', () => {
  process.env.NEXT_PUBLIC_API_BASE = '//example.com';
  const fetch = mock.method(globalThis, 'fetch');
  assert.throws(() => browserEvents(), /Public API unavailable/);
  assert.equal(fetch.mock.callCount(), 0);
});

test('missing or unsafe internal URL fails closed before fetch', async () => {
  const fetch = mock.method(globalThis, 'fetch');
  for (const url of ['', 'file:///etc/passwd', 'http://user:password@backend:8039', 'http://backend:8039/private']) {
    process.env.INTERNAL_API_URL = url;
    await assert.rejects(getBackendHealth(), { message: 'Public API unavailable' });
  }
  assert.equal(fetch.mock.callCount(), 0);
});

test('HTTP, network, invalid JSON and invalid health responses hide diagnostic details', async () => {
  process.env.INTERNAL_API_URL = 'http://backend:8039';
  for (const behavior of [
    async () => new Response('private traceback', { status: 500 }),
    async () => { throw new Error('private network address'); },
    async () => new Response('invalid JSON'),
    async () => Response.json({ status: 'not healthy' }),
  ]) {
    const fetch = mock.method(globalThis, 'fetch', behavior);
    await assert.rejects(getBackendHealth(), { message: 'Public API unavailable' });
    fetch.mock.restore();
  }
});
