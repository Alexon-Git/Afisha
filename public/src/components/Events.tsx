import { formatEventPrice } from '../domain/price';
import type { Event } from '../api/types';
import { eventPeriod } from '../domain/dates';
import { Poster } from './Poster';

export function Status({ event }: { event: Event }) {
  if (event.event_status === 'cancelled') return <p className="notice cancelled" role="status">Мероприятие отменено. Уточните информацию у организатора.</p>;
  if (event.event_status === 'postponed') return <p className="notice" role="status">Мероприятие перенесено. Новую дату уточняйте у организатора.</p>;
  return null;
}

export function EventDate({ value, endAt }: { value: string; endAt?: string | null }) {
  const date = eventPeriod(value, endAt);
  if (!date) return <span>Дата уточняется</span>;
  return <time dateTime={value}>{date.label}{date.aware ? ' (Новосибирск)' : ''}</time>;
}

export function EventGrid({ events }: { events: Event[] }) {
  const visible = events.filter(event => event.publication_status === 'published');
  if (!visible.length) return <div className="empty"><h2>Мероприятий пока нет</h2>
    <p>Попробуйте другие даты или категорию. Новые встречи появятся после редакционной проверки.</p><a href="/events">Смотреть весь каталог</a></div>;
  return <div className="event-grid">{visible.map(event => <article className="event-card" key={event.id}>
    <a className="poster-link" href={`/events/${event.id}`} tabIndex={-1} aria-hidden="true"><Poster url={event.image_url} title={event.title} /></a>
    <div className="card-body"><p className="category">{event.category?.name || 'Деловое мероприятие'}</p>
      <h3><a href={`/events/${event.id}`}>{event.title}</a></h3>
      <p className="event-time"><EventDate value={event.datetime} endAt={event.end_at} /></p>
      <p className="location">{event.location}</p><Status event={event} />
      <div className="card-bottom"><span>{formatEventPrice(event.price)}</span><a href={`/events/${event.id}`} aria-label={`Подробнее о мероприятии «${event.title}»`}>Подробнее <span aria-hidden="true">↗</span></a></div>
    </div>
  </article>)}</div>;
}

export function ApiError() {
  return <div className="empty" role="alert"><h2>Не удалось загрузить мероприятия</h2>
    <p>Сервис временно недоступен. Попробуйте обновить страницу позже.</p><a href="/events">Вернуться в каталог</a></div>;
}

export function DateNote() {
  return <p className="date-note">Для дат без указанного часового пояса сохранено время из афиши. Перед поездкой уточните время и актуальность события у организатора.</p>;
}
