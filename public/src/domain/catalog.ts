import { calendarDate } from './dates.ts';

export interface CatalogQuery { date?: string; date_from?: string; date_to?: string; category?: string; sort?: string }
export type Search = Record<string, string | string[] | undefined>;

export function catalogQuery(search: Search) {
  const filters: CatalogQuery = {};
  let error = '';
  const allowed = new Set(['date', 'date_from', 'date_to', 'category', 'sort', 'page']);
  if (Object.keys(search).some(key => !allowed.has(key))) error = 'В ссылке есть неизвестные параметры.';
  for (const key of allowed) {
    const value = search[key];
    if (Array.isArray(value) || (value && value.length > 150)) error = 'Проверьте параметры ссылки.';
  }
  for (const key of ['date', 'date_from', 'date_to'] as const) {
    const value = search[key];
    if (typeof value !== 'string' || !value) continue;
    if (key === 'date' && ['today', 'tomorrow', 'weekend'].includes(value)) filters.date = value;
    else if (calendarDate(value)) filters[key] = value;
    else error = 'Укажите существующую дату в формате ГГГГ-ММ-ДД.';
  }
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) error = 'Начало периода должно быть раньше окончания.';
  if (typeof search.category === 'string' && search.category) {
    // Match backend slug normalization and the categories.slug VARCHAR(150).
    if (!/[^a-z0-9_-]/.test(search.category) && search.category.length <= 150) filters.category = search.category;
    else error = 'Некорректная категория.';
  }
  if (typeof search.sort === 'string' && search.sort) {
    if (['asc', 'desc'].includes(search.sort)) filters.sort = search.sort;
    else error = 'Некорректная сортировка.';
  }
  let page = 1;
  if (search.page) {
    if (typeof search.page === 'string' && /^[1-9]\d{0,5}$/.test(search.page)) page = Number(search.page);
    else error = 'Некорректный номер страницы.';
  }
  return { filters, page, error };
}

export function catalogLink(filters: CatalogQuery, page = 1): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
  query.set('page', String(page));
  return `/events?${query}`;
}

export function eventId(value: string): number | null {
  return /^[1-9]\d{0,9}$/.test(value) && Number(value) <= 2147483647 ? Number(value) : null;
}
