import { externalUrl } from './safety.ts';

export type Inline = { t: 'text'; v: string } | { t: 'b'; c: Inline[] } | { t: 'i'; c: Inline[] } | { t: 'a'; href: string; c: Inline[] };
export type Block =
  | { t: 'h'; level: 2 | 3 | 4; c: Inline[] } | { t: 'p'; c: Inline[] } | { t: 'q'; c: Inline[] }
  | { t: 'ul' | 'ol'; items: Inline[][] };

/** Only absolute http(s) links and site-relative paths survive; everything else becomes plain text. */
export function safeHref(value: string): string | null {
  if (/^\/(?![\/\\])[^\s\\\u0000-\u001f\u007f]*$/.test(value)) return value;
  return externalUrl(value);
}

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let rest = text;
  const push = (v: string) => { if (v) out.push({ t: 'text', v }); };
  while (rest) {
    const m = /\*\*([^*]+?)\*\*|\*([^*\s][^*]*?)\*|\[([^\]]+)\]\(([^)\s]+)\)/.exec(rest);
    if (!m) { push(rest); break; }
    push(rest.slice(0, m.index));
    if (m[1] !== undefined) out.push({ t: 'b', c: parseInline(m[1]) });
    else if (m[2] !== undefined) out.push({ t: 'i', c: parseInline(m[2]) });
    else {
      const href = safeHref(m[4]);
      if (href) out.push({ t: 'a', href, c: parseInline(m[3]) }); else push(m[3]);
    }
    rest = rest.slice(m.index + m[0].length);
  }
  return out;
}

export function parseMarkdown(source: string): Block[] {
  const blocks: Block[] = [];
  const lines = source.replace(/\r\n?/g, '\n').split('\n');
  let para: string[] = [];
  let list: { t: 'ul' | 'ol'; items: Inline[][] } | null = null;
  let quote: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ t: 'p', c: parseInline(para.join(' ')) });
    if (list) blocks.push(list);
    if (quote.length) blocks.push({ t: 'q', c: parseInline(quote.join(' ')) });
    para = []; list = null; quote = [];
  };
  for (const raw of lines) {
    const line = raw.trim();
    let m;
    if (!line) { flush(); continue; }
    if ((m = /^(#{1,4})\s+(.+)$/.exec(line))) {
      flush(); blocks.push({ t: 'h', level: Math.max(2, m[1].length) as 2 | 3 | 4, c: parseInline(m[2]) });
    } else if ((m = /^[-*]\s+(.+)$/.exec(line))) {
      if (!list || list.t !== 'ul') { flush(); list = { t: 'ul', items: [] }; }
      list.items.push(parseInline(m[1]));
    } else if ((m = /^\d+[.)]\s+(.+)$/.exec(line))) {
      if (!list || list.t !== 'ol') { flush(); list = { t: 'ol', items: [] }; }
      list.items.push(parseInline(m[1]));
    } else if ((m = /^>\s?(.*)$/.exec(line))) {
      if (!quote.length) flush();
      quote.push(m[1]);
    } else {
      if (list || quote.length) flush();
      para.push(line);
    }
  }
  flush();
  return blocks;
}
