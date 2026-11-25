import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import ArticlesAdmin from './ArticlesAdmin';
import { articlesApi } from '../services/api';
jest.mock('../services/api', () => ({
  articlesApi: { list: jest.fn(), create: jest.fn(), update: jest.fn(), publish: jest.fn(), unpublish: jest.fn(), archive: jest.fn(), uploadCover: jest.fn() },
  articleErrorMessage: e => { const d = e?.response?.data?.detail; return d?.fields ? Object.entries(d.fields).map(([k, v]) => `${k}: ${v}`).join('; ') : 'Ошибка запроса'; },
}));
const art = { id: 1, title: 'Статья', slug: 'stat', excerpt: 'e', content: 'c', cover_image_url: null, category: null, seo_title: null,
  seo_description: 'd', author_name: null, publication_status: 'draft', published_at: null, created_at: '', updated_at: '' };
let container, root;
const button = t => Array.from(container.querySelectorAll('button')).find(x => x.textContent === t);
const click = n => act(async () => n.dispatchEvent(new MouseEvent('click', { bubbles: true })));
const field = t => Array.from(container.querySelectorAll('label')).find(x => x.textContent.startsWith(t)).querySelector('input,textarea');
beforeEach(async () => {
  jest.clearAllMocks(); global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
  articlesApi.list.mockResolvedValue({ data: { items: [art], total_pages: 1 } });
  await act(async () => root.render(<ArticlesAdmin />));
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test('saving a draft never publishes and sends no controlled fields', async () => {
  articlesApi.create.mockResolvedValue({ data: art });
  await click(button('Новая статья'));
  act(() => Simulate.change(field('Заголовок'), { target: { value: 'Новая' } }));
  await act(async () => Simulate.submit(container.querySelector('form')));
  const payload = articlesApi.create.mock.calls[0][0];
  expect(payload.title).toBe('Новая');
  expect(payload).not.toHaveProperty('publication_status');
  expect(payload).not.toHaveProperty('published_at');
  expect(articlesApi.publish).not.toHaveBeenCalled();
});

test('API validation errors are shown', async () => {
  articlesApi.update.mockRejectedValue({ response: { data: { detail: { fields: { content: 'Нужен текст' } } } } });
  await click(button('Редактировать'));
  await act(async () => Simulate.submit(container.querySelector('form')));
  expect(container.querySelector('[role=alert]').textContent).toContain('content: Нужен текст');
});

test('publish and unpublish are explicit actions; published slug is locked', async () => {
  articlesApi.publish.mockResolvedValue({ data: { ...art, publication_status: 'published' } });
  await click(button('Редактировать'));
  await click(button('Опубликовать'));
  expect(articlesApi.publish).toHaveBeenCalledWith(1);
  expect(field('Slug').disabled).toBe(true);
  expect(button('Снять с публикации')).toBeTruthy();
});

test('publish is blocked while the form has unsaved changes', async () => {
  articlesApi.update.mockResolvedValue({ data: art });
  articlesApi.publish.mockResolvedValue({ data: { ...art, publication_status: 'published' } });
  await click(button('Редактировать'));
  expect(button('Опубликовать').disabled).toBe(false);
  act(() => Simulate.change(field('Заголовок'), { target: { value: 'Изменено' } }));
  expect(button('Опубликовать').disabled).toBe(true);
  expect(container.querySelector('[role=note]').textContent).toContain('несохранённые');
  await click(button('Опубликовать'));
  expect(articlesApi.publish).not.toHaveBeenCalled();
  await act(async () => Simulate.submit(container.querySelector('form')));
  expect(button('Опубликовать').disabled).toBe(false);
  await click(button('Опубликовать'));
  expect(articlesApi.publish).toHaveBeenCalledWith(1);
});
