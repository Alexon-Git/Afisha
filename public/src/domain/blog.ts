import type { Metadata } from 'next';
import { siteOrigin, imagePath } from './safety.ts';
import { pageMetadata } from './seo.ts';
import type { Article } from '../api/types.ts';

const TZ = 'Asia/Novosibirsk';
export function blogDate(value: string): { text: string; iso: string } | null {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return { iso: d.toISOString(), text: new Intl.DateTimeFormat('ru-RU', { timeZone: TZ, day: 'numeric', month: 'long', year: 'numeric' }).format(d) };
}

export function blogSlug(value: string): string | null {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) && value.length <= 120 ? value : null;
}

export function pageNumber(value: string | string[] | undefined): number {
  const n = typeof value === 'string' && /^[1-9]\d{0,5}$/.test(value) ? Number(value) : 1;
  return n;
}

export function blogListMetadata(page: number, category?: string): Metadata {
  // Filtered and deeper pages are crawlable but not indexed; canonical points at the main list.
  return pageMetadata('Блог для предпринимателей — Бизнес Афиша',
    'Статьи о деловых мероприятиях, нетворкинге и развитии бизнеса.', '/blog', page === 1 && !category);
}

export function articleMetadata(article: Article): Metadata {
  const meta = pageMetadata(article.seo_title || `${article.title} — Бизнес Афиша`,
    article.seo_description || article.excerpt || article.title, `/blog/${article.slug}`);
  const origin = siteOrigin();
  const cover = imagePath(article.cover_image_url);
  const published = blogDate(article.published_at);
  meta.openGraph = { ...meta.openGraph, type: 'article', ...(published ? { publishedTime: published.iso } : {}),
    ...(cover && origin ? { images: [`${origin}${cover}`] } : {}) } as Metadata['openGraph'];
  meta.twitter = { ...meta.twitter, card: cover && origin ? 'summary_large_image' : 'summary',
    ...(cover && origin ? { images: [`${origin}${cover}`] } : {}) } as Metadata['twitter'];
  return meta;
}

export function articleJsonLd(article: Article): string | null {
  const origin = siteOrigin();
  const published = blogDate(article.published_at);
  if (!origin || !published) return null;
  const modified = blogDate(article.updated_at);
  const cover = imagePath(article.cover_image_url);
  return JSON.stringify({
    '@context': 'https://schema.org', '@type': 'Article', headline: article.title,
    description: article.seo_description || article.excerpt || undefined,
    datePublished: published.iso, dateModified: modified && modified.iso !== published.iso ? modified.iso : undefined,
    mainEntityOfPage: `${origin}/blog/${article.slug}`,
    image: cover && origin ? `${origin}${cover}` : undefined,
    author: article.author_name ? { '@type': 'Person', name: article.author_name } : undefined,
  }).replace(/</g, '\\u003c');
}
