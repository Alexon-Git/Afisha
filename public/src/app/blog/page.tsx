import { getArticleCategories, getPublishedArticles } from '../../api/server';
import { ApiUnavailableError } from '../../api/http';
import { blogDate, blogListMetadata, pageNumber } from '../../domain/blog';
import { getAdSlot } from '../../domain/adSlots';
import { imagePath } from '../../domain/safety';
import { AdSlot } from '../../components/AdSlot';
import { ArticleCard, EmptyState } from '../../components/ui';
import { ApiError } from '../../components/Events';

export const dynamic = 'force-dynamic';
type Props = { searchParams: Promise<{ page?: string; category?: string }> };
const PER_PAGE = 12;
const cat = (value?: string) => (typeof value === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) && value.length <= 64 ? value : undefined);
const href = (page: number, category?: string) => {
  const q = new URLSearchParams(); if (category) q.set('category', category); if (page > 1) q.set('page', String(page));
  return q.size ? `/blog?${q}` : '/blog';
};

export async function generateMetadata({ searchParams }: Props) {
  const sp = await searchParams;
  return blogListMetadata(pageNumber(sp.page), cat(sp.category));
}

export default async function BlogPage({ searchParams }: Props) {
  const sp = await searchParams;
  const page = pageNumber(sp.page); const category = cat(sp.category);
  let body; let categories: string[] = [];
  try {
    const [result, cats] = await Promise.all([getPublishedArticles(page, PER_PAGE, category), getArticleCategories().catch(() => [])]);
    categories = cats;
    const preview = process.env.NEXT_PUBLIC_AD_PREVIEW === 'true' && process.env.NODE_ENV !== 'production';
    const cards = result.items.map(a => <ArticleCard key={a.slug} href={`/blog/${a.slug}`} title={a.title} excerpt={a.excerpt || ''}
      tag={a.category || undefined} image={imagePath(a.cover_image_url)} date={blogDate(a.published_at)} />);
    body = result.items.length === 0
      ? <EmptyState title="Статей пока нет" text="Скоро здесь появятся материалы для предпринимателей." href="/events" label="Смотреть афишу" />
      : <><div className="article-grid">{cards.slice(0, 3)}</div>
        <AdSlot config={getAdSlot('blog_feed')} preview={preview} />
        {cards.length > 3 && <div className="article-grid">{cards.slice(3)}</div>}
        {result.total_pages > 1 && <nav className="pagination" aria-label="Страницы блога">
          {page > 1 && <a href={href(page - 1, category)} rel="prev">← Назад</a>}
          <span>Страница {page} из {result.total_pages}</span>
          {page < result.total_pages && <a href={href(page + 1, category)} rel="next">Вперёд →</a>}</nav>}</>;
  } catch (error) {
    if (!(error instanceof ApiUnavailableError)) throw error;
    body = <ApiError />;
  }
  return <main id="main" className="shell main">
    <section className="hero compact"><p className="eyebrow">Бизнес Афиша</p><h1>Блог для предпринимателей</h1>
      <p className="intro">Практические материалы о деловых мероприятиях, нетворкинге и развитии бизнеса.</p></section>
    {categories.length > 0 && <nav className="quick-filters" aria-label="Категории блога"><a href="/blog">Все</a>
      {categories.map(c => <a key={c} href={href(1, c)}>{c}</a>)}</nav>}
    {body}
  </main>;
}
