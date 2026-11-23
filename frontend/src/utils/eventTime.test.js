import { eventInputToInstant, instantToEventInput } from './eventTime';

test.each([
  ['2026-11-23T18:00', '2026-11-23T11:00:00Z'],
  ['2027-01-01T00:30', '2026-12-31T17:30:00Z'],
  ['2026-11-23T00:00', '2026-11-22T17:00:00Z'],
  ['2026-11-23T18:00:42.123456', '2026-11-23T11:00:42.123456Z'],
  ['1900-01-01T05:31:40', '1900-01-01T00:00:00Z'],
  ['2101-01-01T06:59:59.999999', '2100-12-31T23:59:59.999999Z'],
])('Novosibirsk %s round trips to %s without browser TZ or precision loss', (local, instant) => {
  expect(eventInputToInstant(local)).toBe(instant);
  expect(instantToEventInput(instant)).toBe(local.replace(/(\.\d{3})\d+$/, '$1'));
  expect(eventInputToInstant(instantToEventInput(instant), instant)).toBe(instant);
});

test('offsets represent the same instant, not browser-local time', () => {
  expect(instantToEventInput('2026-11-23T18:00:00+07:00')).toBe('2026-11-23T18:00');
});

test.each(['', 'invalid', '2026-02-30T12:00', '2026-13-01T12:00', '2026-11-23',
  '2026-11-23T24:00', '2026-11-23T18:00Z', '2026-11-23T18:00:60',
  '1900-01-01T05:31:39.999999', '2101-01-01T07:00', '9999-12-31T18:00',
  '2026-11-23T18:00:01.1234567', '2016-07-24T02:30', '2014-10-26T01:30',
])('rejects invalid, out-of-range or ambiguous local input %s', input => {
  expect(() => eventInputToInstant(input)).toThrow();
});

test.each(['2026-11-23T18:00:00', '9999-12-31T23:59:59Z', '0001-01-01T00:00:00Z'])('rejects unsupported API instant %s', input => {
  expect(() => instantToEventInput(input)).toThrow();
});


test('native millisecond input preserves original microseconds unless milliseconds are explicitly edited', () => {
  const original = '2026-11-23T11:00:42.123456Z';
  expect(eventInputToInstant('2026-11-24T18:00:42.123', original)).toBe('2026-11-24T11:00:42.123456Z');
  expect(eventInputToInstant('2026-11-24T18:00:42.124', original)).toBe('2026-11-24T11:00:42.124Z');
});
