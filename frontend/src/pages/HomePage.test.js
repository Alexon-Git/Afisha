import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import HomePage from './HomePage';
import { categoriesApi, eventsApi } from '../services/api';

jest.mock('../services/api', () => ({
  categoriesApi: { getAll: jest.fn() }, eventsApi: { getAll: jest.fn() },
}));
jest.mock('../components/Header', () => () => null);
jest.mock('../components/Footer', () => () => null);
jest.mock('../components/Contact', () => () => null);
jest.mock('../components/YandexAdBanner', () => () => null);
jest.mock('../components/EventModal', () => () => null);
jest.mock('../components/DateScroller', () => ({ onDateChange }) => (
  <button onClick={() => onDateChange(new Date(2026, 10, 12), undefined)}>Choose date</button>
));
jest.mock('../components/ThisWeekSection', () => ({ events, loading }) => (
  <div data-testid="week" data-loading={String(loading)}>{events.map(item => item.title).join(',')}</div>
));
jest.mock('../components/CategorySection', () => ({ title, events }) => (
  <div data-testid="category">{title}:{events.map(item => item.title).join(',')}</div>
));

const category = { id: 1, name: 'Business', slug: 'business', is_active: true };
const response = title => ({ data: { items: [{ id: 1, title }] } });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
let container, root;
beforeEach(() => {
  jest.clearAllMocks();
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  categoriesApi.getAll.mockResolvedValue({ data: [category] });
  eventsApi.getAll.mockImplementation((page, limit, params) => Promise.resolve(
    response(params.category ? 'latest category' : 'latest week'),
  ));
});
afterEach(async () => {
  if (root) await act(async () => root.unmount());
  container.remove();
  jest.restoreAllMocks();
});
const render = () => act(async () => root.render(<HomePage />));
const chooseDate = () => act(async () => container.querySelector('button').click());
const week = () => container.querySelector('[data-testid="week"]');

test('an older summary response finishing last cannot overwrite the latest date', async () => {
  const old = deferred();
  eventsApi.getAll.mockReturnValueOnce(old.promise);
  await render();
  await chooseDate();
  expect(week().textContent).toBe('latest week');
  expect(container.textContent).toContain('latest category');
  await act(async () => old.resolve(response('stale week')));
  expect(week().textContent).toBe('latest week');
  expect(container.textContent).not.toContain('stale');
  expect(eventsApi.getAll).toHaveBeenLastCalledWith(1, 6, {
    date_from: '2026-11-12', date_to: '2026-11-12', category: 'business',
  });
});

test('stale category completion cannot clear loading while the latest request is pending', async () => {
  const oldCategory = deferred();
  const latest = deferred();
  eventsApi.getAll.mockImplementation((page, limit, params) => {
    if (!params.date_from) return params.category ? oldCategory.promise : Promise.resolve(response('old week'));
    return params.category ? Promise.resolve(response('latest category')) : latest.promise;
  });
  await render();
  await chooseDate();
  await act(async () => oldCategory.resolve(response('old category')));
  expect(week().dataset.loading).toBe('true');
  expect(week().textContent).toBe('');
  expect(container.querySelector('[data-testid="category"]')).toBeNull();
  await act(async () => latest.resolve(response('latest week')));
  expect(week().dataset.loading).toBe('false');
  expect(week().textContent).toBe('latest week');
  expect(container.textContent).toContain('latest category');
});

test('failure of a stale request does not erase current results', async () => {
  const old = deferred();
  eventsApi.getAll.mockReturnValueOnce(old.promise);
  await render();
  await chooseDate();
  await act(async () => old.reject(new Error('old request failed')));
  expect(week().textContent).toBe('latest week');
  expect(container.textContent).toContain('latest category');
  expect(week().dataset.loading).toBe('false');
});

test.each(['summary', 'category'])('current %s failure clears both result groups', async phase => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
  await render();
  expect(container.textContent).toContain('latest category');
  eventsApi.getAll.mockImplementation((page, limit, params) => {
    if ((phase === 'category') === Boolean(params.category)) return Promise.reject(new Error('current request failed'));
    return Promise.resolve(response('partial result must not be published'));
  });
  await chooseDate();
  expect(week().textContent).toBe('');
  expect(week().dataset.loading).toBe('false');
  expect(container.querySelector('[data-testid="category"]')).toBeNull();
});

test('unmount stops pending work before category requests and state publication', async () => {
  const old = deferred();
  eventsApi.getAll.mockReturnValueOnce(old.promise);
  await render();
  await act(async () => root.unmount());
  root = null;
  await act(async () => old.resolve(response('after unmount')));
  expect(eventsApi.getAll).toHaveBeenCalledTimes(1);
  expect(container.textContent).toBe('');
});
