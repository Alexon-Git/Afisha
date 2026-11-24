// SSR/HTTP regressions with synthetic fixtures and loopback-only listeners.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { cp, readdir, readFile } from 'node:fs/promises';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';
import { fixture, fixtureEvents } from './fixtures.mjs';

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address().port;
}
let events = fixtureEvents();
let unavailable = false;
const requests = [];
const underscoreCategory = { id: 2, name: 'Деловые встречи', slug: 'business_meetings', is_active: true };
const backend = createServer((request, response) => {
  const url = new URL(request.url, 'http://test');
  requests.push(url);
  assert.equal(request.headers.authorization, undefined);
  response.setHeader('Content-Type', 'application/json');
  if (unavailable) {
    response.writeHead(503);
    response.end(JSON.stringify({ error: 'private-traceback-must-not-leak' }));
    return;
  }
  const visible = events.filter(event => event.publication_status === 'published');
  if (url.pathname === '/events/') {
    const page = Number(url.searchParams.get('page') || 1);
    const limit = Number(url.searchParams.get('limit') || 10);
    const items = url.searchParams.get('category') === 'empty' ? [] : visible;
    response.end(JSON.stringify({ items: items.slice((page - 1) * limit, page * limit), page, limit, total_items: items.length, total_pages: Math.ceil(items.length / limit) }));
  } else if (url.pathname.startsWith('/events/')) {
    const event = visible.find(item => item.id === Number(url.pathname.split('/')[2]));
    if (!event) response.writeHead(404);
    response.end(JSON.stringify(event || { detail: 'Event not found' }));
  } else if (url.pathname === '/categories/') response.end(JSON.stringify([fixture.category, underscoreCategory]));
  else if (url.pathname === '/health') response.end(JSON.stringify({ status: 'healthy' }));
  else { response.writeHead(404); response.end('{}'); }
});
const backendPort = await listen(backend);
await cp('.next/static', '.next/standalone/.next/static', { recursive: true });
await cp('public', '.next/standalone/public', { recursive: true });
let app;
async function stop() {
  if (app && app.exitCode === null && app.signalCode === null) {
    const exit = once(app, 'exit');
    app.kill('SIGTERM');
    const watchdog = setTimeout(() => app.kill('SIGKILL'), 5000);
    await exit;
    clearTimeout(watchdog);
  }
}
async function start(siteUrl = '') {
  const reservation = createServer();
  const port = await listen(reservation);
  await new Promise(resolve => reservation.close(resolve));
  const base = `http://127.0.0.1:${port}`;
  let logs = '';
  app = spawn(process.execPath, ['.next/standalone/server.js'], {
    env: { PATH: process.env.PATH, NODE_ENV: 'production', NEXT_TELEMETRY_DISABLED: '1',
      HOSTNAME: '127.0.0.1', PORT: String(port), INTERNAL_API_URL: `http://127.0.0.1:${backendPort}`,
      SITE_URL: siteUrl === 'local' ? base : siteUrl, ALLOW_LOCAL_SITE_URL: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  app.stdout.on('data', value => { logs += value; });
  app.stderr.on('data', value => { logs += value; });
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(`${base}/health`)).ok) return base; } catch { /* wait */ }
    if (app.exitCode !== null) break;
    await delay(100);
  }
  throw new Error(`Standalone failed: ${logs}`);
}
async function html(base, path, status = 200) {
  const response = await fetch(base + path);
  assert.equal(response.status, status, path);
  const text = await response.text();
  if (path === '/' || path.startsWith('/events')) assert.match(response.headers.get('cache-control') || '', /no-store/);
  assert.doesNotMatch(text, /private-traceback-must-not-leak|INTERNAL_API_URL|backend:8039/);
  return text.replace(/<!--[\s\S]*?-->/g, '');
}
try {
  let base = await start();
  const noOrigin = await html(base, '/events/1');
  assert.match(noOrigin, /name="robots" content="noindex, nofollow"/);
  assert.doesNotMatch(noOrigin, /rel="canonical"/);
  assert.match(await html(base, '/robots.txt'), /Disallow: \//);
  await html(base, '/sitemap.xml', 503);
  await stop();
  base = await start('local');
  const home = await html(base, '/');
  assert.match(home, /Встреча предпринимателей/);
  assert.doesNotMatch(home, /Скрытый черновик|Скрытый архив/);
  const script = home.match(/src="([^\"]+\.js[^\"]*)"/);
  assert.ok(script);
  assert.equal((await fetch(new URL(script[1].replaceAll('&amp;', '&'), base))).status, 200);
  assert.ok(requests.some(url => url.searchParams.get('date_from') && url.searchParams.get('date_to') === '9999-12-30'));
  const list = await html(base, '/events?date_from=2026-12-15&date_to=2026-12-16&category=meetings&sort=desc&page=2');
  assert.match(list, /Страница 2 из 9/);
  assert.match(list, /page=3/);
  assert.match(list, /category=meetings/);
  assert.ok(requests.some(url => ['date_from', 'date_to', 'category', 'sort', 'page'].every(key => url.searchParams.has(key))));
  assert.match(list, /<option value="business_meetings">Деловые встречи<\/option>/);
  const underscoreList = await html(base, '/events?category=business_meetings');
  assert.match(underscoreList, /<option value="business_meetings" selected="">Деловые встречи<\/option>/);
  assert.ok(requests.some(url => url.pathname === '/events/' && url.searchParams.get('category') === 'business_meetings'));
  for (const value of ['today', 'tomorrow', 'weekend']) {
    await html(base, `/events?date=${value}`);
    assert.ok(requests.some(url => url.searchParams.get('date') === value));
  }
  assert.match(await html(base, '/events?category=empty'), /Мероприятий пока нет/);
  const before = requests.length;
  assert.match(await html(base, '/events?date=bad'), /Укажите существующую дату/);
  assert.equal(requests.length, before);
  const detail = await html(base, '/events/1');
  assert.match(detail, /Тестовый клуб/);
  assert.match(detail, /href="https:\/\/registration.example.test\/event"/);
  assert.doesNotMatch(detail, /href="https:\/\/payments.example.test/);
  assert.doesNotMatch(detail, /type="application\/ld\+json"/);
  assert.match(detail, new RegExp(`rel="canonical" href="${base}/events/1"`));
  // Real SSR output, no database: the same fixture must agree across all public views.
  const originalEvents = events;
  for (const [price, label] of [[0, 'Бесплатно'], [1500, '1\u00a0500 ₽'], [null, 'Стоимость уточняется']]) {
    events = [{ ...fixture, price }];
    for (const path of ['/', '/events', '/events/1']) {
      const rendered = await html(base, path);
      const priceElement = path === '/events/1'
        ? rendered.match(/<dt>Стоимость<\/dt><dd>([^<]*)<\/dd>/)
        : rendered.match(/class="card-bottom"><span>([^<]*)<\/span>/);
      assert.ok(priceElement, `price element: ${path}`);
      assert.equal(priceElement[1], label, `${path}: price ${price}`);
      if (price === null) assert.doesNotMatch(rendered, /Бесплатно/);
    }
  }
  for (const [end, label] of [[null, '26 ноября 2026 г. · 10:00'],
    ['2026-11-26T11:00:00Z', '26 ноября 2026 г. · 10:00–18:00'],
    ['2026-11-28T11:00:00Z', '26 ноября 2026 г., 10:00 — 28 ноября 2026 г., 18:00']]) {
    events = [{ ...fixture, datetime: '2026-11-26T03:00:00Z', end_at: end }];
    for (const path of ['/', '/events', '/events/1']) {
      const rendered = await html(base, path);
      assert.ok(rendered.includes(label), `${path}: ${label}`);
      if (path === '/events/1') {
        const json = rendered.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
        assert.ok(json);
        assert.equal(JSON.parse(json[1]).endDate, end ? new Date(end).toISOString() : undefined);
      }
    }
  }
  events = originalEvents;
  for (const id of ['4', '5', '99999', 'abc', '2147483648']) await html(base, `/events/${id}`, 404);
  for (const [id, message] of [[2, 'отменено'], [3, 'перенесено']]) {
    const response = await html(base, `/events/${id}`);
    assert.match(response, new RegExp(message));
    assert.doesNotMatch(response, /class="button registration"/);
  }
  const unsafe = await html(base, '/events/6');
  assert.match(unsafe, /&lt;script&gt;window.__injected/);
  assert.doesNotMatch(unsafe, /href="(?:javascript|data):/);
  const json = unsafe.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
  assert.ok(json);
  assert.ok(!json[1].includes('<'));
  assert.match(JSON.parse(json[1]).startDate, /Z$/);
  const sitemap = await html(base, '/sitemap.xml');
  assert.match(sitemap, /\/events\/196<\/loc>/);
  assert.doesNotMatch(sitemap, /\/events\/(4|5)<\/loc>/);
  assert.match(sitemap, /\/events\/2<\/loc>/);
  assert.ok(requests.some(url => url.searchParams.get('page') === '2' && url.searchParams.get('limit') === '100'));
  for (const status of ['cancelled', 'postponed']) {
    events = events.map(event => event.id === 1 ? { ...event, event_status: status } : event);
    const current = await html(base, '/events/1');
    assert.match(current, new RegExp(status === 'cancelled' ? 'отменено' : 'перенесено'));
    assert.doesNotMatch(current, /class="button registration"/);
    assert.match(await html(base, '/sitemap.xml'), /\/events\/1<\/loc>/);
  }
  for (const status of ['draft', 'archived']) {
    events = events.map(event => event.id === 1 ? { ...event, publication_status: status } : event);
    await html(base, '/events/1', 404);
    assert.doesNotMatch(await html(base, '/sitemap.xml'), /\/events\/1<\/loc>/);
  }
  events = fixtureEvents();
  unavailable = true;
  assert.match(await html(base, '/'), /Сервис временно недоступен/);
  assert.match(await html(base, '/events'), /Сервис временно недоступен/);
  assert.match(await html(base, '/events/1'), /Сервис временно недоступен/);
  await html(base, '/sitemap.xml', 503);
  unavailable = false;
  assert.match(await html(base, '/events/1'), /Встреча предпринимателей/);
  assert.ok(requests.every(url => !url.pathname.startsWith('/admin')));
  for (const file of await readdir('.next/static', { recursive: true })) {
    if (file.endsWith('.js')) assert.doesNotMatch(await readFile(`.next/static/${file}`, 'utf8'), /INTERNAL_API_URL|backend:8039/);
  }
  console.log('PASS standalone SSR/HTTP: routes, filters, pagination, visibility, status changes, SEO/sitemap, XSS, API outage and bundle isolation');
  if (process.argv.includes('--serve')) {
    console.log(`BROWSER_QA_URL=${base}`);
    await new Promise(resolve => { process.once('SIGTERM', resolve); process.once('SIGINT', resolve); });
  }
} finally {
  await stop();
  await new Promise(resolve => backend.close(resolve));
}
