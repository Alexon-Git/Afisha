'use client';

import { useState } from 'react';
import type { Category } from '../api/types';
import type { CatalogQuery } from '../domain/catalog';

export function Filters({ filters, categories }: { filters: CatalogQuery; categories: Category[] }) {
  const [pending, setPending] = useState(false);
  return <form action="/events" method="get" className="filters" onSubmit={() => setPending(true)}>
    {filters.date && <input type="hidden" name="date" value={filters.date} />}
    <label>С даты<input type="date" name="date_from" defaultValue={filters.date_from || (filters.date?.includes('-') ? filters.date : '')} max="9999-12-30" /></label>
    <label>По дату<input type="date" name="date_to" defaultValue={filters.date_to || ''} max="9999-12-30" /></label>
    <label>Категория<select name="category" defaultValue={filters.category || ''}><option value="">Все категории</option>
      {categories.filter(category => category.is_active).map(category => <option key={category.id} value={category.slug}>{category.name}</option>)}
    </select></label>
    <label>Порядок<select name="sort" defaultValue={filters.sort || 'asc'}><option value="asc">Сначала ближайшие даты</option><option value="desc">Сначала поздние даты</option></select></label>
    <button disabled={pending} type="submit">{pending ? 'Загружаем…' : 'Показать'}</button><a className="reset" href="/events">Сбросить</a>
  </form>;
}
