import { cache } from 'react';
import { notFound } from 'next/navigation';
import { getPublishedArticle } from '../../../api/server';
import { ApiNotFoundError, ApiUnavailableError } from '../../../api/http';
import { articleJsonLd, articleMetadata, blogDate, blogSlug } from '../../../domain/blog';
import { pageMetadata } from '../../../domain/seo';
import { imagePath } from '../../../domain/safety';
import { Markdown } from '../../../components/Markdown';
import { ApiError } from '../../../components/Events';
import { CategoryBadge } from '../../../components/ui';

export const dynamic = 'force-dynamic';
type Props = { params: Promise<{ slug: string }> };
const load = cache(async (value: string) => {
  const slug = blogSlug(value);
  if (!slug) notFound();
  try { return await getPublishedArticle(slug); }
  catch (error) { if (error instanceof ApiNotFoundError) notFound(); throw error; }
});

export async function generateMetadata({ params }: Props) {
  try { return articleMetadata(await load((await params).slug)); }
  catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
    return pageMetadata('Статья временно недоступна', 'Попробуйте открыть страницу позже.', '/blog', false);
  }
}

export default async function ArticlePage({ params }: Props) {
  let article;
  try { article = await load((await params).slug); } catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
    return <main id="main" className="shell main"><h1>Статья</h1><ApiError /></main>;
  }
  const published = blogDate(article.published_at);
  const updated = blogDate(article.updated_at);
  const cover = imagePath(article.cover_image_url);
  const json = articleJsonLd(article);
  return <main id="main" className="shell main"><article className="article-page">
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><a href="/">Главная</a> / <a href="/blog">Блог</a> / <span aria-current="page">{article.title}</span></nav>
    {article.category && <CategoryBadge>{article.category}</CategoryBadge>}
    <h1>{article.title}</h1>
    <p className="article-meta">{published && <time dateTime={published.iso}>{published.text}</time>}
      {published && updated && updated.text !== published.text && <> · обновлено <time dateTime={updated.iso}>{updated.text}</time></>}
      {article.author_name && <> · {article.author_name}</>}</p>
    {cover && <img className="article-cover" src={cover} alt="" width={960} height={540} />}
    {article.content && <Markdown source={article.content} />}
    <aside className="article-links" aria-label="Афиша"><p>Найдите подходящую встречу в афише:</p>
      <p><a href="/events">Все мероприятия</a> · <a href="/events?date=weekend">Выходные</a> · <a href="/blog">Другие статьи</a></p></aside>
    {json && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />}
  </article></main>;
}
