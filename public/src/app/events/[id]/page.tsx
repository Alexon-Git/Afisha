import { formatEventPrice } from '../../../domain/price';
import { cache } from 'react';
import { notFound } from 'next/navigation';
import { getPublishedEvent } from '../../../api/server';
import { ApiNotFoundError, ApiUnavailableError } from '../../../api/http';
import { eventId } from '../../../domain/catalog';
import { eventJsonLd, pageMetadata } from '../../../domain/seo';
import { externalUrl } from '../../../domain/safety';
import { EventDate, Status, DateNote, ApiError } from '../../../components/Events';
import { Poster } from '../../../components/Poster';
import { Button, CategoryBadge } from '../../../components/ui';

export const dynamic = 'force-dynamic';
type Props = { params: Promise<{ id: string }> };
const load = cache(async (value: string) => {
  const id = eventId(value);
  if (!id) notFound();
  try {
    const event = await getPublishedEvent(id);
    if (event.publication_status !== 'published') notFound();
    return event;
  } catch (error) {
    if (error instanceof ApiNotFoundError) notFound();
    throw error;
  }
});

export async function generateMetadata({ params }: Props) {
  try {
    const event = await load((await params).id);
    return pageMetadata(`${event.title} — Бизнес Афиша`, (event.description || `Деловое мероприятие. ${event.location}`).slice(0, 180), `/events/${event.id}`);
  } catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
    return pageMetadata('Мероприятие временно недоступно', 'Попробуйте открыть страницу позже.', '/events', false);
  }
}

export default async function EventPage({ params }: Props) {
  // Missing/hidden events are resolved before rendering or streaming any body.
  let event;
  try { event = await load((await params).id); } catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
    return <main id="main" className="shell main"><h1>Мероприятие</h1><ApiError /></main>;
  }
  const url = externalUrl(event.event_url);
  const source = externalUrl(event.source);
  const json = eventJsonLd(event);
  const active = event.event_status === 'scheduled';
  return <main id="main" className="shell main detail">
    <a className="back-link" href="/events">← В каталог мероприятий</a>
    <CategoryBadge>{event.category?.name || 'Деловое мероприятие'}</CategoryBadge><h1 className="detail-title">{event.title}</h1>
    <Status event={event} />
    <div className="detail-grid"><div><Poster url={event.image_url} title={event.title} />
      <section className="description"><h2>О мероприятии</h2><p>{event.description || 'Подробности уточняйте у организатора.'}</p></section>
      {source && <a href={source} target="_blank" rel="noopener noreferrer nofollow">Информация из первоисточника ↗</a>}
    </div><aside className="event-summary" aria-label="Информация о мероприятии">
      <dl><dt>Дата и время</dt><dd><EventDate value={event.datetime} endAt={event.end_at} /></dd><dt>Место</dt><dd>{event.location}</dd>
        {event.organizer?.name && <><dt>Организатор</dt><dd>{event.organizer.name}</dd></>}
        <dt>Стоимость</dt><dd>{formatEventPrice(event)}</dd>
      </dl><DateNote />
      {active && url ? <Button href={url} external>Перейти к регистрации ↗</Button> : <p className="notice">{active ? 'Ссылка на регистрацию уточняется.' : 'Регистрация приостановлена. Проверьте актуальную информацию в первоисточнике.'}</p>}
    </aside></div>
    {json && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />}
  </main>;
}
