export function eventDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?$/.exec(value);
  if (!match || !calendarDate(value.slice(0, 10), '9999-12-31') || +match[4] > 23 || +match[5] > 59 || +(match[6] || 0) > 59) return null;
  const aware = Boolean(match[7]);
  if (aware && match[7] !== 'Z' && (+match[7].slice(1, 3) > 23 || +match[7].slice(4) > 59)) return null;
  const instant = aware ? new Date(value) : null;
  if (instant && !Number.isFinite(instant.getTime())) return null;
  const date = new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: aware ? 'Asia/Novosibirsk' : 'UTC',
  }).format(instant || new Date(`${value.slice(0, 10)}T00:00:00Z`));
  const time = instant ? new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Novosibirsk', hourCycle: 'h23',
  }).format(instant) : `${match[4]}:${match[5]}`;
  return { date, time, aware, iso: instant?.toISOString() };
}

export function calendarDate(value: string, last = '9999-12-30'): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value < '0001-01-01' || value > last) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function calendarToday(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Asia/Novosibirsk',
  }).formatToParts(now);
  return ['year', 'month', 'day'].map(name => parts.find(part => part.type === name)?.value).join('-');
}
