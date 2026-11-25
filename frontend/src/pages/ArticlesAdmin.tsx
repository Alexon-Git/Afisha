import React, { useCallback, useEffect, useState } from 'react';
import { Article, ArticleInput, articleErrorMessage, articlesApi } from '../services/api';

const empty: ArticleInput = { title: '', slug: '', excerpt: '', content: '', cover_image_url: '', category: '',
  seo_title: '', seo_description: '', author_name: '' };
const labels: Record<string, string> = { draft: 'Черновик', published: 'Опубликовано', archived: 'Архив' };

/** Safe preview: plain text split into paragraphs; real Markdown is rendered on the server. */
const preview = (text: string) => text.split(/\n{2,}/).map((p, i) => <p key={i} className="mb-2 whitespace-pre-wrap">{p}</p>);

export default function ArticlesAdmin() {
  const [items, setItems] = useState<Article[]>([]);
  const [current, setCurrent] = useState<Article | null>(null);
  const [form, setForm] = useState<ArticleInput>(empty);
  const [editing, setEditing] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setItems((await articlesApi.list()).data.items); }
    catch (e) { setMessage({ error: true, text: articleErrorMessage(e) }); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const open = (article: Article | null) => {
    setCurrent(article); setMessage(null); setShowPreview(false); setEditing(true);
    setForm(article ? Object.fromEntries(Object.keys(empty).map(k => [k, (article as any)[k] ?? ''])) as ArticleInput : empty);
  };
  const set = (key: keyof ArticleInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [key]: e.target.value }));

  const run = async (action: () => Promise<{ data: Article }>, done: string) => {
    setBusy(true); setMessage(null);
    try {
      const saved = (await action()).data;
      setCurrent(saved); setMessage({ error: false, text: done }); await load();
    } catch (e) { setMessage({ error: true, text: articleErrorMessage(e) }); }
    finally { setBusy(false); }
  };
  const save = () => run(() => current ? articlesApi.update(current.id, form) : articlesApi.create(form), 'Сохранено');
  const upload = async (file?: File) => {
    if (!file) return;
    try { setForm(prev => ({ ...prev, cover_image_url: '' })); const r = await articlesApi.uploadCover(file);
      setForm(prev => ({ ...prev, cover_image_url: r.data.image_url })); }
    catch (e) { setMessage({ error: true, text: articleErrorMessage(e) }); }
  };

  const published = current?.publication_status === 'published';
  const field = (key: keyof ArticleInput, label: string, extra: { max?: number; area?: boolean; disabled?: boolean } = {}) =>
    <label className="block">{label}
      {extra.area
        ? <textarea className="w-full border rounded p-2" rows={extra.max && extra.max > 1000 ? 14 : 3} maxLength={extra.max} value={(form[key] as string) ?? ''} onChange={set(key)} />
        : <input className="w-full border rounded p-2" maxLength={extra.max} disabled={extra.disabled} value={(form[key] as string) ?? ''} onChange={set(key)} />}
    </label>;

  return <main className="max-w-7xl mx-auto p-6 space-y-4">
    <a href="/admin/">К мероприятиям</a><h1 className="text-2xl font-bold">Статьи блога</h1>
    {message && <p role={message.error ? 'alert' : 'status'} className={message.error ? 'text-red-700' : 'text-green-700'}>{message.text}</p>}
    {!editing && <>
      <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={() => open(null)}>Новая статья</button>
      <ul className="divide-y bg-white rounded shadow">
        {items.length === 0 && <li className="p-4">Статей пока нет</li>}
        {items.map(a => <li key={a.id} className="p-4 flex justify-between">
          <span>{a.title} <em className="text-gray-500">/{a.slug}</em></span>
          <span>{labels[a.publication_status]} <button className="ml-3 underline" onClick={() => open(a)}>Редактировать</button></span>
        </li>)}
      </ul></>}
    {editing && <form className="space-y-3 bg-white p-4 rounded shadow" onSubmit={e => { e.preventDefault(); save(); }}>
      {current && <p>Статус: <strong>{labels[current.publication_status]}</strong></p>}
      {field('title', 'Заголовок', { max: 200 })}
      {field('slug', 'Slug (латиница; пусто — по заголовку)', { max: 120, disabled: published })}
      {field('excerpt', 'Краткое описание', { max: 500, area: true })}
      {field('category', 'Категория (латиница, например guides)', { max: 64 })}
      {field('author_name', 'Автор (необязательно, только подтверждённое имя)', { max: 120 })}
      <label className="block">Обложка (загрузка)<input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => upload(e.target.files?.[0])} /></label>
      {form.cover_image_url ? <p>Обложка: {form.cover_image_url} <button type="button" className="underline" onClick={() => setForm(p => ({ ...p, cover_image_url: '' }))}>Убрать</button></p> : null}
      {field('content', 'Текст (Markdown: ## заголовки, **жирный**, *курсив*, списки, > цитаты, [ссылки](https://…))', { max: 100000, area: true })}
      {field('seo_title', 'SEO-заголовок', { max: 70 })}
      {field('seo_description', 'SEO-описание', { max: 200, area: true })}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={busy} className="px-4 py-2 bg-blue-600 text-white rounded">Сохранить</button>
        <button type="button" onClick={() => setShowPreview(v => !v)}>Предпросмотр</button>
        {current && !published && <button type="button" disabled={busy} onClick={() => run(() => articlesApi.publish(current.id), 'Опубликовано')}>Опубликовать</button>}
        {published && <button type="button" disabled={busy} onClick={() => run(() => articlesApi.unpublish(current!.id), 'Снято с публикации')}>Снять с публикации</button>}
        {current && current.publication_status !== 'archived' && <button type="button" disabled={busy} onClick={() => run(() => articlesApi.archive(current.id), 'Архивировано')}>В архив</button>}
        <button type="button" onClick={() => { setEditing(false); setCurrent(null); }}>К списку</button>
      </div>
      {published && <p className="text-sm text-gray-600">Сохранение опубликованной статьи сразу меняет сайт. Slug изменить нельзя.</p>}
      {showPreview && <section aria-label="Предпросмотр" className="border p-3"><h2 className="text-xl font-bold">{form.title}</h2>{preview((form.content as string) || '')}
        <p className="text-sm text-gray-500">Упрощённый просмотр: итоговая вёрстка Markdown формируется на сайте.</p></section>}
    </form>}
  </main>;
}
