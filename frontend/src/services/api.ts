import axios from 'axios';

import { PRODUCTION_API_ORIGIN } from '../config/api';

const api = axios.create({
  baseURL: PRODUCTION_API_ORIGIN,
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

export interface Event {
  id: number;
  title: string;
  description?: string;
  datetime: string;
  location: string;
  image_url?: string;
  category?: string;
  creator_id?: number;
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
  location: string;
  image_url?: string;
  category?: string;
}

export interface EventUpdate {
  title?: string;
  description?: string;
  datetime?: string;
  location?: string;
  image_url?: string;
  category?: string;
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
  getAll: (
    page = 1,
    limit = 10,
    params?: EventListParams
  ) => {
    const queryParams: Record<string, string | number> = Object.fromEntries(
      Object.entries({ page, limit, ...params }).filter(([, value]) => value !== undefined && value !== '')
    ) as Record<string, string | number>;

    return api.get<PaginatedEventsResponse>(`/events`, { params: queryParams });
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
