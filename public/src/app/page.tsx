import { getCategories, getPublishedEvents } from '../api/server';
import { calendarToday } from '../domain/dates';
import { EventGrid, ApiError, DateNote } from '../components/Events';
import { DateScroller } from '../components/DateScroller';
import { AdSlot } from '../components/AdSlot';
import { getAdSlot } from '../domain/adSlots';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let content;
  let categories: { id: number; name: string; slug: string }[] = [];
  try {
    const result = await getPublishedEvents(1, 6, { date_from: calendarToday(), date_to: '9999-12-30', sort: 'asc' });
    content = <EventGrid events={result.items} />;
  } catch { content = <ApiError />; }
  try { categories = (await getCategories()).filter(category => category.is_active).slice(0, 6); } catch { /* optional block */ }
  return <main id="main" className="shell main">
    <section className="hero"><p className="eyebrow">Для тех, кто развивает своё дело</p>
      <h1>Хорошие встречи<br />двигают бизнес.</h1>
      <p className="intro">Конференции, бизнес-встречи и новые идеи в Новосибирске. Выберите событие и зарегистрируйтесь у организатора.</p>
      <a className="button" href="/events">Найти мероприятие <span aria-hidden="true">↗</span></a>
      <nav className="quick-filters" aria-label="Быстрый выбор даты"><a href="/events?date=today">Сегодня</a><a href="/events?date=tomorrow">Завтра</a><a href="/events?date=weekend">Выходные</a></nav>
    </section>
    <section className="calendar-panel" aria-labelledby="calendar-heading"><div className="section-heading"><div><p className="eyebrow">Планируйте встречи</p><h2 id="calendar-heading">Календарь мероприятий</h2></div></div><DateScroller /></section>
    <AdSlot config={getAdSlot('home_top')} preview={process.env.NEXT_PUBLIC_AD_PREVIEW === 'true' && process.env.NODE_ENV !== 'production'} />
    <section aria-labelledby="events-heading"><div className="section-heading"><div><p className="eyebrow">В афише города</p><h2 id="events-heading">Ближайшие календарные даты</h2></div><a href="/events">Весь каталог →</a></div>
      <DateNote />{content}
    </section>
    <AdSlot config={getAdSlot('home_middle')} preview={process.env.NEXT_PUBLIC_AD_PREVIEW === 'true' && process.env.NODE_ENV !== 'production'} />
    {categories.length > 0 && <section className="category-panel" aria-labelledby="category-heading"><div className="section-heading"><div><p className="eyebrow">Выберите направление</p><h2 id="category-heading">Темы для развития бизнеса</h2></div></div>
      <div className="category-links">{categories.map(category => <a href={`/events?category=${encodeURIComponent(category.slug)}`} key={category.id}>{category.name}<span aria-hidden="true">↗</span></a>)}</div>
    </section>}
    <section className="partner-panel"><p className="eyebrow">Для организаторов</p><h2>Расскажите о деловом событии</h2><p>В афише публикуются мероприятия после редакционной проверки. Информацию о регистрации ищите на странице организатора.</p></section>
    <AdSlot config={getAdSlot('home_bottom')} preview={process.env.NEXT_PUBLIC_AD_PREVIEW === 'true' && process.env.NODE_ENV !== 'production'} />
  </main>;
}
