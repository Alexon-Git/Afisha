import type { ReactNode } from 'react';

export function Container({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`shell ${className}`.trim()}>{children}</div>;
}

export function SectionHeading({ id, eyebrow, title, action }: { id?: string; eyebrow?: string; title: string; action?: { href: string; label: string } }) {
  return <div className="section-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2 id={id}>{title}</h2></div>
    {action && <a href={action.href}>{action.label}</a>}</div>;
}

export function Button({ href, children, variant = 'primary', external = false }: { href: string; children: ReactNode; variant?: 'primary' | 'secondary'; external?: boolean }) {
  const rel = external ? { target: '_blank', rel: 'noopener noreferrer nofollow' } : {};
  return <a className={`button${variant === 'secondary' ? ' button-secondary' : ''}`} href={href} {...rel}>{children}</a>;
}

export function CategoryBadge({ children }: { children: ReactNode }) {
  return <span className="badge">{children}</span>;
}

export function EmptyState({ title, text, href = '/events', label = 'Смотреть весь каталог', alert = false }: { title: string; text: string; href?: string; label?: string; alert?: boolean }) {
  return <div className="empty" role={alert ? 'alert' : undefined}><h2>{title}</h2><p>{text}</p><a href={href}>{label}</a></div>;
}

/** Content card styles for future SEO pages; no article model is implied. */
export function ArticleCard({ href, title, excerpt, tag }: { href: string; title: string; excerpt: string; tag?: string }) {
  return <article className="article-card">{tag && <CategoryBadge>{tag}</CategoryBadge>}<h3><a href={href}>{title}</a></h3><p>{excerpt}</p></article>;
}
