import 'server-only';
import { readJson, ApiUnavailableError } from './http.ts';
import type { Health, PaginatedEvents, Event, Category } from './types.ts';
import type { CatalogQuery } from '../domain/catalog.ts';

function internalBase(): string {
  const value = process.env.INTERNAL_API_URL;
  if (!value) throw new ApiUnavailableError();
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
        url.search || url.hash || url.pathname !== '/') throw new Error();
    return url.origin;
  } catch { throw new ApiUnavailableError(); }
}

export async function getBackendHealth(): Promise<Health> {
  const result = await readJson<Health>(`${internalBase()}/health`);
  if (result.status !== 'healthy') throw new ApiUnavailableError();
  return result;
}

export function getPublishedEvents(page = 1, limit = 10, filters: CatalogQuery = {}): Promise<PaginatedEvents> {
  const query = new URLSearchParams({ page: String(page), limit: String(limit), ...filters });
  return readJson<PaginatedEvents>(`${internalBase()}/events/?${query}`);
}

export function getPublishedEvent(id: number): Promise<Event> {
  return readJson<Event>(`${internalBase()}/events/${id}`);
}

export function getCategories(): Promise<Category[]> {
  return readJson<Category[]>(`${internalBase()}/categories/`);
}
