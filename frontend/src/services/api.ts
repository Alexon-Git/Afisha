import axios from 'axios';

import { API_BASE_URL } from '../config/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Интерцептор для добавления токена авторизации
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Интерцептор для обработки ошибок авторизации
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url: string | undefined = error.config?.url;
      const onLoginRequest = url?.includes('/auth/login');
      const isOnLoginPage = typeof window !== 'undefined' && window.location.pathname === '/admin/login';
      // Do NOT redirect for invalid login attempt; let the page show the error
      if (onLoginRequest || isOnLoginPage) {
        return Promise.reject(error);
      }
      localStorage.removeItem('access_token');
      if (typeof window !== 'undefined') {
        window.location.href = '/admin/login';
      }
    }
    return Promise.reject(error);
  }
);

export interface Category {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
}

export const normalizeCategoryList = (data: unknown): Category[] => {
  if (Array.isArray(data)) {
    return data as Category[];
  }
  if (data && typeof data === 'object') {
    const items = (data as { items?: unknown }).items;
    if (Array.isArray(items)) {
      return items as Category[];
    }
  }
  return [];
};

export type PublicationStatus = 'draft' | 'published' | 'archived';
export type EventStatus = 'scheduled' | 'cancelled' | 'postponed';
export interface Organizer { id: number; name: string; }

export interface Event {
  organizer?: { name: string } | null;
  id: number;
  title: string;
  description?: string;
  datetime: string;
  end_at?: string | null;
  location: string;
  image_url?: string | null;
  category_id?: number | null;
  category?: Category | null;
  creator_id?: number;
  verified_at?: string | null;
  publication_status: PublicationStatus;
  event_status: EventStatus;
  price?: number | null;
  rating?: number | null;
  discount?: number | null;
  payment_url?: string | null;
  organizer_id?: number | null;
  event_url?: string | null;
  source?: string | null;
}

export interface PaginatedEventsResponse {
  items: Event[];
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
}

export interface EventListParams {
  date?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  sort?: 'asc' | 'desc';
}

export interface EventCreate {
  title: string;
  description?: string;
  datetime: string;
  end_at?: string | null;
  location: string;
  image_url?: string | null;
  category_id?: number | null;
  price?: number | null;
  rating?: number | null;
  discount?: number | null;
  payment_url?: string | null;
  organizer_id?: number | null;
  event_url?: string | null;
  source?: string | null;
}

export interface EventUpdate {
  title?: string;
  description?: string;
  datetime?: string;
  end_at?: string | null;
  location?: string;
  image_url?: string | null;
  category_id?: number | null;
  price?: number | null;
  rating?: number | null;
  discount?: number | null;
  payment_url?: string | null;
  organizer_id?: number | null;
  event_url?: string | null;
  source?: string | null;
}

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const eventsApi = {
  getAdminAll: (page = 1, limit = 50) =>
    api.get<PaginatedEventsResponse>('/admin/events/', { params: { page, limit } }),
  getAdminById: (id: number) => api.get<Event>(`/admin/events/${id}`),
  verify: (id: number) => api.post<Event>(`/admin/events/${id}/verify`),
  changePublication: (id: number, publication_status: 'draft' | 'published' | 'archived') =>
    api.patch<Event>(`/admin/events/${id}/publication`, { publication_status }),
  changeStatus: (id: number, event_status: 'scheduled' | 'cancelled' | 'postponed') =>
    api.patch<Event>(`/admin/events/${id}/status`, { event_status }),
  getAll: (
    page = 1,
    limit = 10,
    params?: EventListParams
  ) => {
    const queryParams: Record<string, string | number> = Object.fromEntries(
      Object.entries({ page, limit, ...params }).filter(([, value]) => value !== undefined && value !== '')
    ) as Record<string, string | number>;

    return api.get<PaginatedEventsResponse>(`/events/`, { params: queryParams });
  },
  getById: (id: number) => api.get<Event>(`/events/${id}`),
  create: (data: EventCreate) => api.post<Event>('/events/', data),
  update: (id: number, data: EventUpdate) => api.put<Event>(`/events/${id}`, data),
  delete: (id: number) => api.delete(`/events/${id}`),
  uploadImage: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<{ image_url: string }>('/events/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

export const organizersApi = {
  getAll: () => api.get<Organizer[]>('/admin/organizers/'),
};

export interface CategoryCreatePayload {
  name: string;
  slug?: string;
  is_active?: boolean;
}

export interface CategoryUpdatePayload {
  name?: string;
  slug?: string;
  is_active?: boolean;
}

export const categoriesApi = {
  getAll: async (includeInactive = false) => {
    const response = await api.get<unknown>(`/categories/`, {
      params: { include_inactive: includeInactive },
    });
    return {
      ...response,
      data: normalizeCategoryList(response.data),
    } as typeof response & { data: Category[] };
  },
  create: (data: CategoryCreatePayload) => api.post<Category>('/categories/', data),
  update: (id: number, data: CategoryUpdatePayload) => api.put<Category>(`/categories/${id}`, data),
  delete: (id: number) => api.delete(`/categories/${id}`),
};

export const authApi = {
  login: (data: LoginData) => {
    const body = `grant_type=password&username=${encodeURIComponent(data.username)}&password=${encodeURIComponent(data.password)}`;
    return api.post<TokenResponse>('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  me: () => api.get<User>('/auth/me'),
};

export default api;

export interface ImportSource {
  id: number; name: string; base_url: string; state: string; access_method: string;
  permission_basis: string | null; permission_reference: string | null;
  terms_url: string | null; terms_checked_at: string | null; review_due_at: string | null;
  robots_state: string; policy_version: number;
}
export interface ImportRun {
  id: string; source_id: number; status: string; requested_url: string;
  error_code: string | null; record_errors: {code: string; attempt: number}[];
  records_seen: number; candidates_created: number; candidates_unchanged: number;
}
export interface ImportCandidate {
  id: number; source_id: number; revision: number; title: string | null;
  review_status: string; start_at: string | null; reviewed_revision: number | null;
  source_url: string; original_start: string | null; time_resolution: string;
  city: string | null; venue_name: string | null; address: string | null;
  warnings: string[]; field_provenance: Record<string, unknown>;
  proposed_organizer_id: number | null; linked_event_id: number | null;
  organizer_name: string | null; organizer_url: string | null; official_event_url: string | null;
  price_kind: string; price_amount: string | null; currency: string | null; proposed_event_status: string | null;
  matches: {id: number; event_id: number | null; reason_codes: string[]; score: string}[];
}
export const importApi = {
  sources: () => api.get<ImportSource[]>('/admin/import/sources'),
  runs: () => api.get<ImportRun[]>('/admin/import/runs'),
  start: (source_id: number, url: string, key: string) => api.post<ImportRun>('/admin/import/runs', {source_id,url}, {headers:{'Idempotency-Key':key}}),
  candidates: (page = 1) => api.get<{items: ImportCandidate[]; total_pages: number}>('/admin/import/candidates', {params:{page,limit:20}}),
  candidate: (id: number) => api.get<ImportCandidate>(`/admin/import/candidates/${id}`),
  approve: (c: ImportCandidate, dismissed: boolean) => api.post<ImportCandidate>(`/admin/import/candidates/${c.id}/approve`, {
    expected_revision:c.revision, time_decision:'accept', organizer_decision:'unresolved',
    match_decisions:c.matches.map(m => ({match_id:m.id,decision:dismissed ? 'not_a_duplicate' : 'defer'})),
  }),
  reject: (c: ImportCandidate, review_note: string) => api.post<ImportCandidate>(`/admin/import/candidates/${c.id}/reject`, {expected_revision:c.revision,review_note}),
  promote: (c: ImportCandidate) => api.post<ImportCandidate>(`/admin/import/candidates/${c.id}/promote`, {expected_revision:c.revision}),
  link: (c: ImportCandidate, event_id: number) => api.post<ImportCandidate>(`/admin/import/candidates/${c.id}/link`, {expected_revision:c.revision,event_id}),
  edit: (c: ImportCandidate, data: {start_at: string; city: string; venue_name: string; review_note: string}) => api.patch<ImportCandidate>(`/admin/import/candidates/${c.id}`, {expected_revision:c.revision,...data}),
  recheck: (c: ImportCandidate, key: string) => api.post<ImportRun>(`/admin/import/candidates/${c.id}/recheck`, {}, {headers:{'Idempotency-Key':key}}),
};
