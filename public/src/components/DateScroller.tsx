import type { CatalogQuery } from '../domain/catalog';
import { calendarDays, calendarHref } from '../domain/calendar';

/** URL-driven calendar (server component): the selected state is derived only from the query string. */
export function DateScroller({ filters = {}, days = 30 }: { filters?: CatalogQuery; days?: number }) {
  const fmt = (options: Intl.DateTimeFormatOptions, iso: string) => new Intl.DateTimeFormat('ru-RU', { ...options, timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`));
  return <nav className="date-scroller" aria-label="Выбрать дату мероприятия">
    {calendarDays(filters, days).map(day => <a key={day.iso} href={calendarHref(filters, day.iso)} aria-current={day.selected ? 'date' : undefined}
      className={`date-tile${day.selected ? ' selected' : ''}${[0, 6].includes(day.weekday) ? ' weekend' : ''}`}>
      <span>{fmt({ weekday: 'short' }, day.iso)}</span><strong>{day.day}</strong><span>{fmt({ month: 'short' }, day.iso)}</span>
    </a>)}
  </nav>;
}
