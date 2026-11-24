import { test } from 'node:test';
import assert from 'node:assert/strict';
import { eventDate, eventPeriod, calendarToday } from '../src/domain/dates.ts';
import { catalogQuery, catalogLink, eventId } from '../src/domain/catalog.ts';
import { externalUrl, imagePath, siteOrigin } from '../src/domain/safety.ts';
import { eventJsonLd, pageMetadata } from '../src/domain/seo.ts';
import { fixture } from './fixtures.mjs';

test('legacy components and explicit zoned dates have separate stable paths', () => {
  assert.deepEqual(eventDate('2026-12-15T18:30:00'), { date: '15 декабря 2026 г.', time: '18:30', aware: false, iso: undefined });
  const aware = eventDate('2026-12-15T18:30:00+07:00');
  assert.equal(aware?.time, '18:30');
  assert.equal(aware?.iso, '2026-12-15T11:30:00.000Z');
  assert.equal(calendarToday(new Date('2026-12-31T18:00:00Z')), '2027-01-01');
  for (const value of ['not-a-date', '2026-02-30T12:00:00', '2026-12-15T25:00:00', '2026-12-15T12:00:00+25:00']) assert.equal(eventDate(value), null);
});

test('query validation rejects invalid, duplicated and unbounded input', () => {
  for (const search of [{ date: '2026-02-30' }, { page: '-1' }, { page: '99999999' }, { date: ['today', 'tomorrow'] },
    { date_from: '2026-12-16', date_to: '2026-12-15' }, { category: '../admin' }, { sort: 'DROP' }, { include_unpublished: '1' }]) {
    assert.ok(catalogQuery(search).error, JSON.stringify(search));
  }
  const query = { date_from: '2026-12-15', date_to: '2026-12-16', category: 'meetings', sort: 'desc' };
  assert.deepEqual(catalogQuery({ ...query, page: '2' }), { filters: query, page: 2, error: '' });
  const url = new URL(catalogLink(query, 3), 'http://test');
  assert.equal(url.searchParams.get('category'), 'meetings');
  assert.equal(url.searchParams.get('page'), '3');
  assert.equal(eventId('01'), null);
  assert.equal(eventId('2147483648'), null);
});

test('category query matches backend slug characters and storage length', () => {
  for (const category of ['business_meetings', 'business-meetings', '_business--meetings_', '-', '_', 'a'.repeat(150)]) {
    const result = catalogQuery({ category });
    assert.equal(result.error, '', category);
    assert.equal(result.filters.category, category);
    assert.equal(new URL(catalogLink(result.filters), 'http://test').searchParams.get('category'), category);
  }
  for (const category of ['a'.repeat(151), 'a'.repeat(10000), '../admin', '/admin/events', 'https://example.com',
    '//example.com', 'business/meetings', 'business\\meetings', 'business%5fmeetings', '%2e%2e',
    'business?limit=100', 'business#meetings', 'business meetings', 'Business', 'бизнес',
    'business\n', '\tbusiness', 'business\r', 'business\0', 'business\x7f']) {
    const result = catalogQuery({ category });
    assert.ok(result.error, JSON.stringify(category));
    assert.equal(result.filters.category, undefined);
  }
  assert.ok(catalogQuery({ category: ['business_meetings', 'meetings'] }).error);
});

test('untrusted links and images fail closed', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,a', '//example.com', 'https://user:pass@example.com', 'https://a.com/\n', 'https:\\example.com']) assert.equal(externalUrl(value), null);
  assert.equal(externalUrl('https://example.com/event'), 'https://example.com/event');
  for (const value of ['https://remote/image.png', '/static/uploads/../../secret', '/static/uploads/%61.png']) assert.equal(imagePath(value), null);
  assert.equal(imagePath('/static/uploads/' + 'a'.repeat(32) + '.png'), '/static/uploads/' + 'a'.repeat(32) + '.png');
  assert.equal(imagePath('/static/uploads/' + 'a'.repeat(32) + '.png?v=1#preview'), '/static/uploads/' + 'a'.repeat(32) + '.png');
});

test('SITE_URL and metadata have a safe missing-origin path', () => {
  const original = process.env.SITE_URL;
  const allow = process.env.ALLOW_LOCAL_SITE_URL;
  delete process.env.SITE_URL;
  delete process.env.ALLOW_LOCAL_SITE_URL;
  try {
    for (const value of ['http://localhost:3001', 'https://example.com/path', 'https://user:pass@example.com', 'file:///tmp', 'https://example.com?q=x']) assert.equal(siteOrigin(value), null);
    const metadata = pageMetadata('Title', 'Description', '/events/1');
    assert.deepEqual(metadata.robots, { index: false, follow: false });
    assert.equal(metadata.alternates, undefined);
    process.env.SITE_URL = 'https://afisha.example.test';
    assert.equal(pageMetadata('Title', 'Description', '/events/1').alternates?.canonical, 'https://afisha.example.test/events/1');
  } finally {
    if (original === undefined) delete process.env.SITE_URL; else process.env.SITE_URL = original;
    if (allow === undefined) delete process.env.ALLOW_LOCAL_SITE_URL; else process.env.ALLOW_LOCAL_SITE_URL = allow;
  }
});

test('JSON-LD omits naive dates and escapes editorial script payloads', () => {
  const original = process.env.SITE_URL;
  process.env.SITE_URL = 'https://afisha.example.test';
  try {
    assert.equal(eventJsonLd(fixture), null);
    const result = eventJsonLd({ ...fixture, datetime: '2026-12-15T18:30:00+07:00', title: '</script><script>alert(1)</script>', event_status: 'cancelled' });
    assert.ok(result);
    assert.ok(!result.includes('<'));
    assert.equal(JSON.parse(result).eventStatus, 'https://schema.org/EventCancelled');
    assert.equal(JSON.parse(result).offers, undefined);
    assert.equal(eventJsonLd({ ...fixture, publication_status: 'draft' }), null);
  } finally { if (original === undefined) delete process.env.SITE_URL; else process.env.SITE_URL = original; }
});


test('period formatting uses Novosibirsk for missing, same-day and multi-day ends', () => {
  const start = '2026-11-26T03:00:00Z';
  assert.equal(eventPeriod(start)?.label, '26 ноября 2026 г. · 10:00');
  assert.equal(eventPeriod(start, null)?.label, eventPeriod(start)?.label);
  assert.equal(eventPeriod(start, '2026-11-26T11:00:00Z')?.label, '26 ноября 2026 г. · 10:00–18:00');
  assert.equal(eventPeriod(start, '2026-11-28T11:00:00Z')?.label, '26 ноября 2026 г., 10:00 — 28 ноября 2026 г., 18:00');
  assert.equal(eventPeriod('2026-11-26T16:30:00Z', '2026-11-26T17:30:00Z')?.label,
    '26 ноября 2026 г., 23:30 — 27 ноября 2026 г., 00:30');
  assert.equal(eventPeriod(start, 'invalid')?.label, eventPeriod(start)?.label);
});

test('JSON-LD endDate is explicit and optional, never synthesized', () => {
  process.env.SITE_URL = 'https://example.org';
  try {
    const event = { ...fixture, datetime: '2026-11-26T03:00:00Z' };
    assert.equal(JSON.parse(eventJsonLd(event)!).endDate, undefined);
    assert.equal(JSON.parse(eventJsonLd({ ...event, end_at: null })!).endDate, undefined);
    assert.equal(JSON.parse(eventJsonLd({ ...event, end_at: '2026-11-28T18:00:00+07:00' })!).endDate, '2026-11-28T11:00:00.000Z');
  } finally { delete process.env.SITE_URL; }
});
