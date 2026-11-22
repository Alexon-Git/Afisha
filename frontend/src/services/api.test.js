import axios from 'axios';
import { eventsApi, authApi } from './api';

jest.mock('axios', () => {
  const client = { get: jest.fn(), post: jest.fn(), patch: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } };
  return { create: config => { if (config) client.defaults = config; return client; } };
});

test('admin client uses same-origin API and controlled editorial endpoints', () => {
  const client = axios.create();
  expect(client.defaults.baseURL).toBe('/api');
  authApi.login({ username: 'editor', password: 'test-only-value' });
  expect(client.post).toHaveBeenLastCalledWith('/auth/login', expect.any(String), expect.any(Object));
  authApi.me();
  expect(client.get).toHaveBeenLastCalledWith('/auth/me');
  eventsApi.verify(17);
  expect(client.post).toHaveBeenLastCalledWith('/admin/events/17/verify');
  eventsApi.changePublication(17, 'draft');
  expect(client.patch).toHaveBeenLastCalledWith('/admin/events/17/publication', { publication_status: 'draft' });
  eventsApi.changeStatus(17, 'cancelled');
  expect(client.patch).toHaveBeenLastCalledWith('/admin/events/17/status', { event_status: 'cancelled' });
});

test('editor reads use protected endpoints and public reads stay public', () => {
  const client = axios.create();
  eventsApi.getAdminAll(2, 50);
  expect(client.get).toHaveBeenLastCalledWith('/admin/events/', { params: { page: 2, limit: 50 } });
  eventsApi.getAdminById(17);
  expect(client.get).toHaveBeenLastCalledWith('/admin/events/17');
  eventsApi.getAll(1, 10);
  expect(client.get).toHaveBeenLastCalledWith('/events/', { params: { page: 1, limit: 10 } });
});
