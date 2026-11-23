import { formatInTimeZone, fromZonedTime } from 'date-fns-tz';

export const EVENT_TIME_ZONE = 'Asia/Novosibirsk';
const MIN_INSTANT = '1900-01-01T00:00:00.000000Z';
const MAX_INSTANT = '2100-12-31T23:59:59.999999Z';
const LOCAL = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?$/;
const INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/;
const PATTERN = "yyyy-MM-dd'T'HH:mm:ss";
const error = () => new Error('Укажите корректное время Новосибирска в диапазоне UTC 1900–2100');

// Keep PostgreSQL microseconds outside JS Date's millisecond precision.
const utcString = (date: Date, fraction = ''): string => {
  if (!Number.isFinite(date.getTime())) throw error();
  const utc = date.toISOString().replace(/\.\d{3}Z$/, `.${fraction.padEnd(6, '0')}Z`);
  if (utc < MIN_INSTANT || utc > MAX_INSTANT) throw error();
  return utc;
};

export const instantToEventInput = (instant: string): string => {
  const match = INSTANT.exec(instant);
  if (!match) throw error();
  const date = new Date(instant); // Explicit offset only; never a datetime-local string.
  utcString(date, match[1]);
  const local = formatInTimeZone(date, EVENT_TIME_ZONE, PATTERN);
  // Native datetime-local supports milliseconds. The exact original instant stays
  // in the editor snapshot; preserve sub-millisecond digits on date-only edits.
  const fraction = (match[1] || '').slice(0, 3).replace(/0+$/, '');
  return fraction ? `${local}.${fraction}` : local.replace(/:00$/, '');
};

export const eventInputToInstant = (input: string, originalInstant?: string): string => {
  const match = LOCAL.exec(input);
  if (!match) throw error();
  const local = `${match[1]}T${match[2]}:${match[3] || '00'}`;
  const date = fromZonedTime(local, EVENT_TIME_ZONE);
  if (!Number.isFinite(date.getTime()) || formatInTimeZone(date, EVENT_TIME_ZONE, PATTERN) !== local) {
    throw error(); // Reject invalid calendar dates and DST gaps, never silently normalize.
  }
  // Historical clock rollbacks can make a local wall time ambiguous.
  for (const hours of [-2, -1, 1, 2]) {
    if (formatInTimeZone(new Date(date.getTime() + hours * 3600000), EVENT_TIME_ZONE, PATTERN) === local) {
      throw error();
    }
  }
  let fraction = match[4] || '';
  if (originalInstant) {
    const original = INSTANT.exec(originalInstant);
    if (!original) throw error();
    const originalFraction = (original[1] || '').padEnd(6, '0');
    if (fraction.padEnd(3, '0') === originalFraction.slice(0, 3)) {
      fraction = originalFraction;
    }
  }
  const utc = utcString(date, fraction);
  return utc.replace(/\.0{6}Z$/, 'Z').replace(/(\.\d*?[1-9])0+Z$/, '$1Z');
};
