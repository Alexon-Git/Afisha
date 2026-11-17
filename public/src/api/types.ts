// Mirrors backend/app/schemas/{event,category}.py. Datetimes remain opaque
// strings: the timezone semantics of historical event dates are unresolved.
export type PublicationStatus = 'draft' | 'published' | 'archived';
export type EventStatus = 'scheduled' | 'cancelled' | 'postponed';

export interface Category {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface Event {
  id: number;
  title: string;
  description: string | null;
  datetime: string;
  location: string;
  image_url: string | null;
  category_id: number | null;
  price: number | null;
  rating: number | null;
  discount: number | null;
  payment_url: string | null;
  creator_id: number | null;
  category: Category | null;
  organizer_id: number | null;
  organizer?: { name: string } | null;
  event_url: string | null;
  source: string | null;
  verified_at: string | null;
  publication_status: PublicationStatus;
  event_status: EventStatus;
}

export interface PaginatedEvents {
  items: Event[];
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
}

export interface Health { status: 'healthy' }
