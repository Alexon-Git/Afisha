import { getPublishedEvents } from '../api/server';
import { calendarToday } from '../domain/dates';
import { EventGrid, ApiError, DateNote } from '../components/Events';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  let content;
  try {
    const result = await getPublishedEvents(1, 6, { date_from: calendarToday(), date_to: '9999-12-30', sort: 'asc' });
    content = <EventGrid events={result.items} />;
  } catch { content = <ApiError />; }
  return <main id="main" className="shell main">
    <section className="hero"><p className="eyebrow">Для тех, кто развивает своё дело</p>
      <h1>Хорошие встречи<br />двигают бизнес.</h1>
      <p className="intro">Конференции, бизнес-встречи и новые идеи в Новосибирске. Выберите событие и зарегистрируйтесь у организатора.</p>
      <a className="button" href="/events">Найти мероприятие <span aria-hidden="true">↗</span></a>
      <nav className="quick-filters" aria-label="Быстрый выбор даты"><a href="/events?date=today">Сегодня</a><a href="/events?date=tomorrow">Завтра</a><a href="/events?date=weekend">Выходные</a></nav>
    </section>
    <section aria-labelledby="events-heading"><div className="section-heading"><div><p className="eyebrow">В афише города</p><h2 id="events-heading">Ближайшие календарные даты</h2></div><a href="/events">Весь каталог →</a></div>
      <DateNote />{content}
    </section>
  </main>;
}
