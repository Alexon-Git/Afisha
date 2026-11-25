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
  end_at?: string | null;
  location: string;
  image_url: string | null;
  category_id: number | null;
  price: number | null;
  price_kind?: 'unknown' | 'free' | 'fixed' | 'from' | 'range' | 'by_request';
  price_amount?: string | null;
  price_max?: string | null;
  currency?: string | null;

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

export interface Article {
  slug: string; title: string; excerpt: string | null; content: string | null;
  cover_image_url: string | null; category: string | null; seo_title: string | null;
  seo_description: string | null; author_name: string | null; published_at: string; updated_at: string;
}
export interface PaginatedArticles { items: Article[]; page: number; limit: number; total_items: number; total_pages: number }
