import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import AdminDashboard from './AdminDashboard';
import { categoriesApi, eventsApi } from '../services/api';

jest.mock('../services/api', () => ({
  categoriesApi: { getAll: jest.fn() },
  eventsApi: { getAll: jest.fn(), delete: jest.fn(), create: jest.fn(), update: jest.fn() },
}));
jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));
jest.mock('react-hot-toast', () => ({
  __esModule: true, default: { error: jest.fn(), success: jest.fn() },
}));

const item = id => ({ id, title: `Event ${id}`, datetime: '2026-11-12T12:00:00', location: 'Novosibirsk' });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const response = (items, total = items.length, page = 1) => ({
  data: { items, page, limit: 50, total_items: total, total_pages: Math.ceil(total / 50) },
});

let container, root, rows;
beforeEach(() => {
  jest.clearAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  rows = Array.from({ length: 51 }, (_, i) => item(i + 1));
  categoriesApi.getAll.mockResolvedValue({ data: [] });
  eventsApi.getAll.mockImplementation((page, limit) => Promise.resolve(response(
    rows.slice((page - 1) * limit, page * limit), rows.length, page,
  )));
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.restoreAllMocks();
});
const render = () => act(async () => root.render(<AdminDashboard />));
const button = text => Array.from(container.querySelectorAll('button')).find(node => node.textContent === text);
const click = node => act(async () => node.dispatchEvent(new MouseEvent('click', { bubbles: true })));

test('uses server pages and displays totals without loading the whole catalog', async () => {
  await render();
  expect(container.textContent).toContain('Всего мероприятий: 51');
  expect(button('Предыдущая').disabled).toBe(true);
  expect(container.querySelectorAll('button[aria-label^="Удалить Event"]')).toHaveLength(50);
  await click(button('Следующая'));
  expect(eventsApi.getAll).toHaveBeenLastCalledWith(2, 50);
  expect(container.textContent).toContain('Страница 2 из 2');
  expect(container.querySelectorAll('button[aria-label^="Удалить Event"]')).toHaveLength(1);
  expect(button('Следующая').disabled).toBe(true);
  await click(button('Предыдущая'));
  expect(eventsApi.getAll).toHaveBeenLastCalledWith(1, 50);
});

test('deleting the last event on a page returns to an existing page', async () => {
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  eventsApi.delete.mockImplementation(async id => { rows = rows.filter(row => row.id !== id); });
  await render();
  await click(button('Следующая'));
  await click(container.querySelector('[aria-label="Удалить Event 51"]'));
  expect(eventsApi.delete).toHaveBeenCalledWith(51);
  expect(container.textContent).toContain('Страница 1 из 1');
  expect(container.textContent).toContain('Всего мероприятий: 50');
  expect(eventsApi.getAll).toHaveBeenLastCalledWith(1, 50);
});

test('creating an event from page two refreshes page one and the total', async () => {
  eventsApi.create.mockImplementation(async () => { rows.push(item(52)); });
  await render();
  await click(button('Следующая'));
  await click(button('Добавить мероприятие'));
  const form = container.querySelector('form');
  act(() => {
    Simulate.change(form.querySelector('input[type="text"]'), { target: { value: 'Created' } });
    Simulate.change(form.querySelector('input[type="datetime-local"]'), { target: { value: '2026-11-12T12:00' } });
    Simulate.change(form.querySelectorAll('input[type="text"]')[1], { target: { value: 'Novosibirsk' } });
  });
  await act(async () => Simulate.submit(form));
  expect(eventsApi.create).toHaveBeenCalledTimes(1);
  expect(eventsApi.getAll).toHaveBeenLastCalledWith(1, 50);
  expect(container.textContent).toContain('Страница 1 из 2');
  expect(container.textContent).toContain('Всего мероприятий: 52');
  expect(container.querySelector('form')).toBeNull();
});

test('shows loading, error with retry, and empty states', async () => {
  const request = deferred();
  eventsApi.getAll.mockReturnValueOnce(request.promise);
  await render();
  expect(container.textContent).toContain('Загрузка мероприятий...');
  expect(button('Следующая').disabled).toBe(true);
  await act(async () => request.reject(new Error('test failure')));
  expect(container.querySelector('[role="alert"]').textContent).toContain('Ошибка');
  rows = [];
  await click(button('Повторить загрузку'));
  expect(container.textContent).toContain('Нет мероприятий');
  expect(container.textContent).toContain('Всего мероприятий: 0');
});

test('stale page request cannot replace a refreshed list', async () => {
  const stale = deferred();
  eventsApi.getAll.mockReturnValueOnce(stale.promise);
  await render();
  // A successful creation triggers a refresh even while the initial list loads.
  eventsApi.create.mockResolvedValue({ data: item(52) });
  await click(button('Добавить мероприятие'));
  const form = container.querySelector('form');
  act(() => {
    Simulate.change(form.querySelector('input[type="text"]'), { target: { value: 'Created' } });
    Simulate.change(form.querySelector('input[type="datetime-local"]'), { target: { value: '2026-11-12T12:00' } });
    Simulate.change(form.querySelectorAll('input[type="text"]')[1], { target: { value: 'Novosibirsk' } });
  });
  await act(async () => Simulate.submit(form));
  await act(async () => stale.resolve(response([item(999)], 999)));
  expect(container.textContent).toContain('Всего мероприятий: 51');
  expect(container.querySelector('[aria-label="Удалить Event 999"]')).toBeNull();
});

test('removing the image explicitly sends null rather than omitting the update', async () => {
  rows = [{ ...item(1), image_url: '/static/uploads/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png' }];
  eventsApi.update.mockResolvedValue({ data: item(1) });
  await render();
  await click(container.querySelector('[aria-label="Редактировать Event 1"]'));
  await click(container.querySelector('[aria-label="Удалить изображение"]'));
  await act(async () => Simulate.submit(container.querySelector('form')));
  expect(eventsApi.update).toHaveBeenCalledWith(1, expect.objectContaining({ image_url: null }));
});
