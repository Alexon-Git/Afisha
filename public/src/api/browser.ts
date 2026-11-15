'use client';

import { readJson, ApiUnavailableError } from './http.ts';
import type { PaginatedEvents } from './types.ts';

export function getPublishedEvents(page = 1, limit = 10): Promise<PaginatedEvents> {
  const base = process.env.NEXT_PUBLIC_API_BASE || '/api';
  // Same-origin path only. This is a client, not an arbitrary-target proxy.
  if (!/^\/(?!\/)[a-zA-Z0-9/_-]*$/.test(base)) throw new ApiUnavailableError();
  const query = new URLSearchParams({ page: String(page), limit: String(limit) });
  return readJson<PaginatedEvents>(`${base.replace(/\/$/, '')}/events/?${query}`);
}
