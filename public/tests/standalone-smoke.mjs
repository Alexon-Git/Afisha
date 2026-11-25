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
const article = (n, over = {}) => ({ slug: `stat-${n}`, title: `Статья ${n}`, excerpt: `Кратко ${n}`, content: '## Раздел\n\nТекст **важный**.', cover_image_url: null,
  category: n % 2 ? 'guides' : 'news', seo_title: null, seo_description: `Описание ${n}`, author_name: null,
  published_at: '2026-11-26T10:00:00Z', updated_at: '2026-11-26T10:00:00Z', ...over, status: over.status || 'published' });
let articles = [...Array.from({ length: 14 }, (_, i) => article(i + 1)),
  article(90, { slug: 'draft-one', title: 'Скрытая статья', status: 'draft' }),
  article(91, { slug: 'xss', title: 'XSS </script>', content: '<script>window.__injected=1</script>\n\n[bad](javascript:alert(1)) [ok](https://example.test/x)', author_name: 'Иван' })];
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
  if (url.pathname.startsWith('/articles/')) {
    const live = articles.filter(a => a.status === 'published');
    if (url.pathname === '/articles/categories') { response.end(JSON.stringify([...new Set(live.map(a => a.category))].sort())); return; }
    if (url.pathname === '/articles/') {
      const page = Number(url.searchParams.get('page') || 1), limit = Number(url.searchParams.get('limit') || 12);
      const category = url.searchParams.get('category');
      const items = live.filter(a => !category || a.category === category);
      response.end(JSON.stringify({ items: items.slice((page - 1) * limit, page * limit).map(({ status, ...a }) => a), page, limit, total_items: items.length, total_pages: Math.ceil(items.length / limit) }));
      return;
    }
    const found = live.find(a => a.slug === decodeURIComponent(url.pathname.slice('/articles/'.length)));
    if (!found) response.writeHead(404);
    const { status, ...body } = found || { detail: 'Article not found' };
    response.end(JSON.stringify(body));
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
  if (path === '/' || path.startsWith('/events') || path.startsWith('/blog')) assert.match(response.headers.get('cache-control') || '', /no-store/);
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
  for (const [pricing, label] of [
    [{price_kind:'free'}, 'Бесплатно'], [{price_kind:'unknown'}, 'Стоимость уточняется'],
    [{price_kind:'by_request'}, 'По запросу'],
    [{price_kind:'fixed',price_amount:'1500.50',currency:'RUB'}, '1\u00a0500,50 ₽'],
    [{price_kind:'fixed',price_amount:'20.50',currency:'USD'}, '20,50 USD'],
    [{price_kind:'from',price_amount:'1000',currency:'RUB'}, 'От 1\u00a0000 ₽'],
    [{price_kind:'range',price_amount:'1000',price_max:'2500',currency:'RUB'}, '1\u00a0000–2\u00a0500 ₽'],
    [{price_kind:'fixed',price_amount:'99999999999999.9999',currency:'EUR'}, '99\u00a0999\u00a0999\u00a0999\u00a0999,9999 EUR'],
  ]) {
    events = [{ ...fixture, price:null, ...pricing }];
    for (const path of ['/', '/events', '/events/1']) {
      assert.ok((await html(base,path)).includes(label), `${path}: ${label}`);
    }
  }
  events = originalEvents;
  // Blog: SSR list, pagination, categories, ad slot, article page, 404, XSS, JSON-LD, sitemap.
  const blog = await html(base, '/blog');
  assert.match(blog, /<h1[^>]*>Блог для предпринимателей<\/h1>/);
  assert.match(blog, /Статья 1</);
  assert.doesNotMatch(blog, /Скрытая статья/);
  assert.match(blog, new RegExp(`rel="canonical" href="${base}/blog"`));
  assert.match(blog, /Страница 1 из 2/);
  assert.match(blog, /blog\?page=2/);
  assert.match(blog, /category=guides/);
  assert.doesNotMatch(blog, /class="ad-slot/, 'ad hidden when unconfigured in production');
  const page2 = await html(base, '/blog?page=2');
  assert.match(page2, /name="robots" content="noindex, nofollow"/);
  assert.match(await html(base, '/blog?page=abc'), /Страница 1 из 2/);
  const filtered = await html(base, '/blog?category=news');
  assert.match(filtered, /name="robots" content="noindex, nofollow"/);
  assert.ok(requests.some(url => url.pathname === '/articles/' && url.searchParams.get('category') === 'news'));
  const one = await html(base, '/blog/stat-1');
  assert.equal((one.match(/<h1[ >]/g) || []).length, 1);
  assert.match(one, /<h2>Раздел<\/h2>/);
  assert.match(one, /<strong>важный<\/strong>/);
  assert.match(one, new RegExp(`rel="canonical" href="${base}/blog/stat-1"`));
  assert.match(one, /property="og:type" content="article"/);
  const articleLd = JSON.parse(one.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
  assert.equal(articleLd['@type'], 'Article');
  assert.equal(articleLd.datePublished, '2026-11-26T10:00:00.000Z');
  assert.equal(articleLd.author, undefined);
  assert.equal(articleLd.image, undefined);
  const xss = await html(base, '/blog/xss');
  assert.doesNotMatch(xss, /<script>window\.__injected/);
  assert.match(xss, /&lt;script&gt;window\.__injected/);
  assert.doesNotMatch(xss, /href="javascript:/);
  assert.match(xss, /href="https:\/\/example.test\/x"[^>]*rel="noopener noreferrer nofollow"/);
  assert.ok(!xss.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1].includes('<'));
  for (const slug of ['draft-one', 'missing', 'Bad_Slug', '..%2Fx']) await html(base, `/blog/${slug}`, 404);
  const blogMap = await html(base, '/sitemap.xml');
  assert.match(blogMap, /<loc>[^<]*\/blog<\/loc>/);
  assert.match(blogMap, /\/blog\/stat-14<\/loc>/);
  assert.doesNotMatch(blogMap, /draft-one/);
  assert.ok(requests.every(url => !url.pathname.startsWith('/admin')));
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
  assert.match(await html(base, '/blog'), /Сервис временно недоступен/);
  assert.match(await html(base, '/blog/stat-1'), /Сервис временно недоступен/);
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
