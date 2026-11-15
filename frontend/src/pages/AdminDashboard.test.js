import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import AdminDashboard from './AdminDashboard';
import { categoriesApi, eventsApi } from '../services/api';

jest.mock('../services/api', () => ({
  categoriesApi: { getAll: jest.fn() },
  eventsApi: { getAll: jest.fn(), getAdminAll: jest.fn(), delete: jest.fn(), create: jest.fn(), update: jest.fn(), uploadImage: jest.fn() },
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
  eventsApi.getAdminAll.mockImplementation((page, limit) => Promise.resolve(response(
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
  expect(eventsApi.getAll).not.toHaveBeenCalled();
  expect(container.textContent).toContain('Всего мероприятий: 51');
  expect(button('Предыдущая').disabled).toBe(true);
  expect(container.querySelectorAll('button[aria-label^="Удалить Event"]')).toHaveLength(50);
  await click(button('Следующая'));
  expect(eventsApi.getAdminAll).toHaveBeenLastCalledWith(2, 50);
  expect(container.textContent).toContain('Страница 2 из 2');
  expect(container.querySelectorAll('button[aria-label^="Удалить Event"]')).toHaveLength(1);
  expect(button('Следующая').disabled).toBe(true);
  await click(button('Предыдущая'));
  expect(eventsApi.getAdminAll).toHaveBeenLastCalledWith(1, 50);
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
  expect(eventsApi.getAdminAll).toHaveBeenLastCalledWith(1, 50);
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
  expect(eventsApi.getAdminAll).toHaveBeenLastCalledWith(1, 50);
  expect(container.textContent).toContain('Страница 1 из 2');
  expect(container.textContent).toContain('Всего мероприятий: 52');
  expect(container.querySelector('form')).toBeNull();
});

test('shows loading, error with retry, and empty states', async () => {
  const request = deferred();
  eventsApi.getAdminAll.mockReturnValueOnce(request.promise);
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
  eventsApi.getAdminAll.mockReturnValueOnce(stale.promise);
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
  expect(eventsApi.update).toHaveBeenCalledWith(1, { image_url: null });
});

const openEditor = async (values = {}) => {
  rows = [{
    ...item(1), publication_status: 'published', description: null,
    image_url: null, category: null, price: null, rating: 0, discount: 15,
    payment_url: 'https://example.com/register?ref=1#tickets', ...values,
  }];
  categoriesApi.getAll.mockResolvedValue({ data: [
    { id: 1, name: 'Business', slug: 'business', is_active: true },
    { id: 2, name: 'Meetup', slug: 'meetup', is_active: true },
  ] });
  eventsApi.update.mockResolvedValue({ data: rows[0] });
  await render();
  await click(container.querySelector('[aria-label="Редактировать Event 1"]'));
  return container.querySelector('form');
};
const change = (node, value) => act(() => Simulate.change(node, { target: { value } }));

test('published description edit sends only description, never the untouched naive datetime', async () => {
  const form = await openEditor();
  change(form.querySelector('textarea'), 'Updated description');
  // Clicking the actual submit button exercises the editor save action.
  await click(button('Обновить'));
  expect(eventsApi.update).toHaveBeenCalledTimes(1);
  expect(eventsApi.update).toHaveBeenCalledWith(1, { description: 'Updated description' });
});

test.each([0, 125.5, null])('price edit preserves %s and omits every unchanged field', async price => {
  const form = await openEditor({ price: 100 });
  change(form.querySelectorAll('input[type="number"]')[0], price === null ? '' : String(price));
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).toHaveBeenCalledWith(1, { price });
});

test.each([
  [null, 2], [{ id: 1, name: 'Business' }, null],
])('category change from %j to %s sends only category_id', async (category, categoryId) => {
  const form = await openEditor({ category });
  change(form.querySelector('select'), categoryId === null ? '' : String(categoryId));
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).toHaveBeenCalledWith(1, { category_id: categoryId });
});

test.each([
  {},
  { description: '', image_url: '', payment_url: '', price: 0, rating: null, discount: 0 },
  { category: { id: 1, name: 'Business' }, price: 100.5, rating: 8.5, discount: null },
])('unchanged editor values do not send PUT (%j)', async values => {
  const form = await openEditor(values);
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).not.toHaveBeenCalled();
  expect(container.querySelector('form')).toBeNull();
});

test('reverting changes and normalizing numeric and empty URL input does not send PUT', async () => {
  const form = await openEditor({ price: 0, payment_url: null });
  change(form.querySelector('textarea'), 'Temporary');
  change(form.querySelector('textarea'), '');
  change(form.querySelectorAll('input[type="number"]')[0], '0.00');
  change(form.querySelector('input[type="url"]'), '   ');
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).not.toHaveBeenCalled();
});

test.each([
  ['textarea', '', { description: '' }],
  ['input[type="url"]', '', { payment_url: null }],
  ['input[placeholder="Введите название мероприятия"]', 'New title', { title: 'New title' }],
  ['input[placeholder="Введите место проведения"]', 'New location', { location: 'New location' }],
  ['input[placeholder="Например, 8.5"]', '0', { rating: 0 }],
  ['input[placeholder="Например, 15"]', '', { discount: null }],
])('editing %s sends the explicit changed value', async (selector, value, payload) => {
  const form = await openEditor({ description: 'Original', rating: 8.5 });
  change(form.querySelector(selector), value);
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).toHaveBeenCalledWith(1, payload);
});

test.each([null, '/static/uploads/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png'])(
  'uploading an image from %s sends only the new image URL', async imageUrl => {
    const form = await openEditor({ image_url: imageUrl });
    const next = '/static/uploads/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.webp';
    const file = new File(['test'], 'poster.webp', { type: 'image/webp' });
    eventsApi.uploadImage.mockResolvedValue({ data: { image_url: next } });
    await act(async () => Simulate.change(form.querySelector('input[type="file"]'), {
      target: { files: [file] },
    }));
    await act(async () => Simulate.submit(form));
    expect(eventsApi.uploadImage).toHaveBeenCalledWith(file);
    expect(eventsApi.update).toHaveBeenCalledWith(1, { image_url: next });
  },
);

test('explicitly changing a draft date retains the existing ISO conversion contract', async () => {
  const form = await openEditor({ publication_status: 'draft' });
  const datetime = '2026-12-15T15:30';
  change(form.querySelector('input[type="datetime-local"]'), datetime);
  await act(async () => Simulate.submit(form));
  expect(eventsApi.update).toHaveBeenCalledWith(1, { datetime: new Date(datetime).toISOString() });
});

test('creation keeps the full EventCreate contract', async () => {
  eventsApi.create.mockResolvedValue({ data: item(2) });
  await render();
  await click(button('Добавить мероприятие'));
  const form = container.querySelector('form');
  change(form.querySelectorAll('input[type="text"]')[0], 'Created');
  change(form.querySelectorAll('input[type="text"]')[1], 'Novosibirsk');
  change(form.querySelector('input[type="datetime-local"]'), '2026-12-15T15:30');
  await act(async () => Simulate.submit(form));
  expect(eventsApi.create).toHaveBeenCalledWith({
    title: 'Created', location: 'Novosibirsk', description: '',
    datetime: new Date('2026-12-15T15:30').toISOString(), image_url: null,
    category_id: null, price: null, rating: null, discount: null, payment_url: null,
  });
  expect(eventsApi.update).not.toHaveBeenCalled();
});
