import { calendarToday } from './dates.ts';
import { catalogLink, type CatalogQuery } from './catalog.ts';

export interface CalendarDay { iso: string; day: number; weekday: number; selected: boolean }

/** Consecutive Novosibirsk calendar dates starting today. Pure UTC date arithmetic, no browser zone. */
export function calendarDays(filters: CatalogQuery = {}, count = 30, now = new Date()): CalendarDay[] {
  const base = new Date(`${calendarToday(now)}T00:00:00Z`);
  const from = filters.date_from, to = filters.date_to || from;
  return Array.from({ length: count }, (_, index) => {
    const day = new Date(base.getTime() + index * 86400000);
    const iso = day.toISOString().slice(0, 10);
    return { iso, day: day.getUTCDate(), weekday: day.getUTCDay(), selected: !!from && iso >= from && iso <= (to as string) };
  });
}

/** Selection state machine: no selection/range/other day -> that day; single day + later day -> range. */
export function nextSelection(filters: CatalogQuery, iso: string): CatalogQuery {
  const keep = { category: filters.category, sort: filters.sort };
  const { date_from: from, date_to: to } = filters;
  if (from && (!to || to === from) && iso > from) return { ...keep, date_from: from, date_to: iso };
  return { ...keep, date_from: iso, date_to: iso };
}

export function calendarHref(filters: CatalogQuery, iso: string): string {
  return catalogLink(nextSelection(filters, iso)).replace(/&page=1$/, '');
}
