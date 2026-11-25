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

/** Content card for blog and future SEO pages. */
export function ArticleCard({ href, title, excerpt, tag, image, date }: { href: string; title: string; excerpt: string; tag?: string; image?: string | null; date?: { text: string; iso: string } | null }) {
  return <article className="article-card">
    {image && <a href={href} tabIndex={-1} aria-hidden="true"><img className="article-card-img" src={image} alt="" loading="lazy" width={640} height={360} /></a>}
    {tag && <CategoryBadge>{tag}</CategoryBadge>}<h3><a href={href}>{title}</a></h3>
    {excerpt && <p>{excerpt}</p>}{date && <time dateTime={date.iso}>{date.text}</time>}</article>;
}
