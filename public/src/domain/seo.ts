import type { Metadata } from 'next';
import type { Event } from '../api/types.ts';
import { eventDate } from './dates.ts';
import { externalUrl, siteOrigin } from './safety.ts';

export function pageMetadata(title: string, description: string, path: string, index = true): Metadata {
  const origin = siteOrigin();
  const url = origin ? `${origin}${path}` : undefined;
  return {
    title, description, robots: { index: Boolean(origin) && index, follow: Boolean(origin) && index },
    alternates: url ? { canonical: url } : undefined,
    openGraph: { title, description, type: 'website', locale: 'ru_RU', ...(url ? { url } : {}) },
    twitter: { card: 'summary', title, description },
  };
}

export function eventJsonLd(event: Event): string | null {
  const date = eventDate(event.datetime);
  const end = event.end_at ? eventDate(event.end_at) : null;
  const origin = siteOrigin();
  if (!origin || !date?.aware || !date.iso || event.publication_status !== 'published') return null;
  const statuses = { scheduled: 'EventScheduled', cancelled: 'EventCancelled', postponed: 'EventPostponed' };
  return JSON.stringify({
    '@context': 'https://schema.org', '@type': 'Event', name: event.title,
    description: event.description || undefined, startDate: date.iso,
    endDate: end?.aware && end.iso && Date.parse(end.iso) > Date.parse(date.iso) ? end.iso : undefined,
    eventStatus: `https://schema.org/${statuses[event.event_status]}`,
    url: `${origin}/events/${event.id}`,
    location: { '@type': 'Place', name: event.location },
    organizer: event.organizer?.name ? { '@type': 'Organization', name: event.organizer.name } : undefined,
    sameAs: externalUrl(event.event_url) || undefined,
  }).replace(/</g, '\\u003c');
}
