import { getCategories, getPublishedEvents } from '../../api/server';
import { catalogLink, catalogQuery, type Search } from '../../domain/catalog';
import { pageMetadata } from '../../domain/seo';
import { EventGrid, ApiError, DateNote } from '../../components/Events';
import { Filters } from '../../components/Filters';
import { DateScroller } from '../../components/DateScroller';

export const dynamic = 'force-dynamic';
export async function generateMetadata({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  return pageMetadata('Каталог деловых мероприятий — Бизнес Афиша', 'Встречи, конференции и деловые события Новосибирска. Выберите даты и категорию.', '/events', !Object.values(search).some(Boolean));
}

export default async function Catalog({ searchParams }: { searchParams: Promise<Search> }) {
  const { filters, page, error } = catalogQuery(await searchParams);
  if (error) return <main id="main" className="shell main"><h1>Проверьте ссылку</h1><p role="alert">{error}</p><a href="/events">Открыть каталог</a></main>;
  try {
    const [result, categories] = await Promise.all([getPublishedEvents(page, 12, filters), getCategories()]);
    return <main id="main" className="shell main">
      <div className="page-heading"><p className="eyebrow">Новосибирск · деловые события</p><h1>Каталог мероприятий</h1></div>
      <nav className="quick-filters" aria-label="Быстрый выбор даты">{[['today', 'Сегодня'], ['tomorrow', 'Завтра'], ['weekend', 'Выходные']].map(([value, label]) => <a key={value} className={filters.date === value ? 'selected' : ''} href={catalogLink({ category: filters.category, date: value })}>{label}</a>)}</nav>
      <section className="calendar-panel" aria-label="Календарь"><DateScroller filters={filters} /></section>
      <Filters filters={filters} categories={categories} />
      <div className="section-heading"><h2>Мероприятия</h2><p>Найдено {result.total_items}</p></div>
      <DateNote />
      {page > result.total_pages && result.total_pages > 0 ? <div className="empty"><h2>На этой странице больше нет событий</h2><a href={catalogLink(filters)}>К началу выдачи</a></div> : <EventGrid events={result.items} />}
      {result.total_pages > 1 && <nav className="pagination" aria-label="Страницы каталога">
        {page > 1 && <a href={catalogLink(filters, page - 1)}>← Назад</a>}
        <span>Страница {page} из {result.total_pages}</span>
        {page < result.total_pages && <a href={catalogLink(filters, page + 1)}>Далее →</a>}
      </nav>}
    </main>;
  } catch { return <main id="main" className="shell main"><h1>Каталог мероприятий</h1><ApiError /></main>; }
}
