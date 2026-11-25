import test from 'node:test';
import assert from 'node:assert/strict';
import { calendarDays, nextSelection, calendarHref } from '../src/domain/calendar.ts';
import { catalogQuery } from '../src/domain/catalog.ts';

const NOW = new Date('2026-12-15T05:00:00Z');
const query = (href: string) => Object.fromEntries(new URL(href, 'http://t').searchParams);

test('single day, range, reset and restart', () => {
  const one = nextSelection({}, '2026-12-16');
  assert.deepEqual(one, { category: undefined, sort: undefined, date_from: '2026-12-16', date_to: '2026-12-16' });
  assert.equal(nextSelection(one, '2026-12-20').date_to, '2026-12-20');
  assert.equal(nextSelection(one, '2026-12-20').date_from, '2026-12-16');
  const range = nextSelection(one, '2026-12-20');
  assert.deepEqual([nextSelection(range, '2026-12-22').date_from, nextSelection(range, '2026-12-22').date_to], ['2026-12-22', '2026-12-22']);
  assert.equal(nextSelection(one, '2026-12-10').date_from, '2026-12-10');
});

test('URL round trip keeps filters and agrees with highlighted days', () => {
  const href = calendarHref({ category: 'meetings', sort: 'desc', date_from: '2026-12-16', date_to: '2026-12-16' }, '2026-12-18');
  assert.deepEqual(query(href), { category: 'meetings', sort: 'desc', date_from: '2026-12-16', date_to: '2026-12-18' });
  assert.ok(!href.includes('page='));
  const parsed = catalogQuery(query(href));
  assert.equal(parsed.error, '');
  assert.deepEqual(calendarDays(parsed.filters, 10, NOW).filter(d => d.selected).map(d => d.iso), ['2026-12-16', '2026-12-17', '2026-12-18']);
  assert.ok(!calendarHref({ date: 'today' }, '2026-12-16').includes('date=today'));
});

test('month and year boundaries', () => {
  const days = calendarDays({}, 5, new Date('2026-12-30T05:00:00Z')).map(d => d.iso);
  assert.deepEqual(days, ['2026-12-30', '2026-12-31', '2027-01-01', '2027-01-02', '2027-01-03']);
  assert.deepEqual(calendarDays({}, 3, new Date('2028-02-28T05:00:00Z')).map(d => d.iso), ['2028-02-28', '2028-02-29', '2028-03-01']);
});

test('start day follows Asia/Novosibirsk, not UTC or host zone', () => {
  assert.equal(calendarDays({}, 1, new Date('2026-12-31T20:00:00Z'))[0].iso, '2027-01-01');
  assert.equal(calendarDays({}, 1, new Date('2026-12-31T16:59:00Z'))[0].iso, '2026-12-31');
});
