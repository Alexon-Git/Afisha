import axios from 'axios';
import { eventsApi } from './api';

jest.mock('axios', () => {
  const client = { get: jest.fn(), interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } };
  return { create: () => client };
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
