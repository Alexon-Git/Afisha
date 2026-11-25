import type { ReactNode } from 'react';
import { parseMarkdown, type Inline } from '../domain/markdown';

function inline(nodes: Inline[]): ReactNode {
  return nodes.map((n, i) => n.t === 'text' ? n.v : n.t === 'b' ? <strong key={i}>{inline(n.c)}</strong>
    : n.t === 'i' ? <em key={i}>{inline(n.c)}</em>
    : <a key={i} href={n.href} {...(n.href.startsWith('/') ? {} : { target: '_blank', rel: 'noopener noreferrer nofollow' })}>{inline(n.c)}</a>);
}

/** React escapes all text; no raw HTML is ever injected. */
export function Markdown({ source }: { source: string }) {
  return <div className="prose">{parseMarkdown(source).map((b, i) => {
    if (b.t === 'h') { const H = `h${b.level}` as 'h2' | 'h3' | 'h4'; return <H key={i}>{inline(b.c)}</H>; }
    if (b.t === 'p') return <p key={i}>{inline(b.c)}</p>;
    if (b.t === 'q') return <blockquote key={i}>{inline(b.c)}</blockquote>;
    const L = b.t; return <L key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</L>;
  })}</div>;
}
