import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import App from './App';
import { authApi, categoriesApi, eventsApi } from './services/api';

jest.mock('./services/api', () => ({
  authApi: { login: jest.fn(), me: jest.fn() },
  categoriesApi: { getAll: jest.fn() },
  eventsApi: { getAdminAll: jest.fn() },
}));
jest.mock('react-hot-toast', () => ({ __esModule: true, default: { error: jest.fn(), success: jest.fn() }, Toaster: () => null }));
let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  localStorage.clear();
  jest.clearAllMocks();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  authApi.me.mockResolvedValue({ data: { username: 'editor', is_admin: true } });
  authApi.login.mockResolvedValue({ data: { access_token: 'test-token' } });
  categoriesApi.getAll.mockResolvedValue({ data: [] });
  eventsApi.getAdminAll.mockResolvedValue({ data: { items: [], total_items: 0, total_pages: 0 } });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});

test('direct admin route redirects unauthorized visitor within basename', async () => {
  window.history.replaceState(null, '', '/admin');
  await act(async () => root.render(<App />));
  expect(window.location.pathname).toBe('/admin/login');
  expect(container.querySelector('form')).not.toBeNull();
  expect(container.textContent).not.toMatch(/admin123|Тестовые данные/);
});

test('direct login, login success and logout use /admin routes', async () => {
  window.history.replaceState(null, '', '/admin/login');
  await act(async () => root.render(<App />));
  const username = container.querySelector('input[name="username"]');
  const password = container.querySelector('input[name="password"]');
  await act(async () => {
    username.value = 'editor'; Simulate.change(username);
    password.value = 'test-only-password'; Simulate.change(password);
    Simulate.submit(container.querySelector('form'));
  });
  expect(authApi.login).toHaveBeenCalledWith({ username: 'editor', password: 'test-only-password' });
  expect(window.location.pathname).toBe('/admin');
  expect(container.textContent).toContain('Админ-панель');
  const logout = [...container.querySelectorAll('button')].find(button => button.textContent === 'Выйти');
  await act(async () => Simulate.click(logout));
  expect(window.location.pathname).toBe('/admin/login');
  expect(localStorage.getItem('access_token')).toBeNull();
});
