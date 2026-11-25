import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMarkdown, parseInline, safeHref } from '../src/domain/markdown.ts';
import { articleJsonLd, blogDate, blogSlug, pageNumber } from '../src/domain/blog.ts';

test('markdown supports headings, lists, quotes, emphasis and safe links', () => {
  const blocks = parseMarkdown('# Один\n## Два\n### Три\n\nТекст **жирный** и *курсив*.\n\n- a\n- b\n\n1. x\n2. y\n\n> цитата');
  assert.deepEqual(blocks.map(b => b.t), ['h', 'h', 'h', 'p', 'ul', 'ol', 'q']);
  // H1 in content is demoted: the page owns the single H1.
  assert.deepEqual(blocks.filter(b => b.t === 'h').map(b => (b as any).level), [2, 2, 3]);
});

test('markdown never produces raw HTML nodes or unsafe links', () => {
  const inline = parseInline('<script>alert(1)</script> [x](javascript:alert(1)) [y](data:text/html,1) [z](//evil.test) [ok](https://example.test/a) [rel](/events)');
  const links = inline.filter(n => n.t === 'a').map(n => (n as any).href);
  assert.deepEqual(links, ['https://example.test/a', '/events']);
  assert.ok(inline.some(n => n.t === 'text' && n.v.includes('<script>')), 'script stays plain text for React to escape');
  assert.equal(safeHref('\\\\evil'), null);
  assert.equal(safeHref('/\\evil'), null);
});

test('slug, page and date helpers fail closed', () => {
  assert.equal(blogSlug('good-slug-1'), 'good-slug-1');
  for (const bad of ['Bad', '../x', 'a b', '', 'a--b', 'x'.repeat(121)]) assert.equal(blogSlug(bad), null, bad);
  assert.equal(pageNumber('3'), 3);
  for (const bad of ['0', '-1', 'abc', '1e3', undefined, ['1']]) assert.equal(pageNumber(bad as any), 1);
  assert.equal(blogDate('2026-11-26T20:00:00Z')?.text, '27 ноября 2026 г.'); // Asia/Novosibirsk, UTC+7
  assert.equal(blogDate('nope'), null);
});

test('Article JSON-LD omits unconfirmed fields and escapes markup', () => {
  const prev = [process.env.SITE_URL];
  process.env.SITE_URL = 'https://afisha.example.test';
  try {
    const base = { slug: 's', title: 'T </script>', excerpt: null, content: null, cover_image_url: null, category: null,
      seo_title: null, seo_description: null, author_name: null, published_at: '2026-11-26T10:00:00Z', updated_at: '2026-11-26T10:00:00Z' };
    const json = articleJsonLd(base)!;
    assert.ok(!json.includes('<'));
    const data = JSON.parse(json);
    assert.equal(data.datePublished, '2026-11-26T10:00:00.000Z');
    for (const key of ['author', 'image', 'dateModified', 'publisher']) assert.equal(data[key], undefined, key);
    const full = JSON.parse(articleJsonLd({ ...base, author_name: 'Имя', cover_image_url: '/static/uploads/' + 'a'.repeat(32) + '.png', updated_at: '2026-11-27T10:00:00Z' })!);
    assert.equal(full.author.name, 'Имя');
    assert.equal(full.image, 'https://afisha.example.test/static/uploads/' + 'a'.repeat(32) + '.png');
    assert.equal(full.dateModified, '2026-11-27T10:00:00.000Z');
    delete process.env.SITE_URL;
    assert.equal(articleJsonLd(base), null);
  } finally { if (prev[0] === undefined) delete process.env.SITE_URL; else process.env.SITE_URL = prev[0]; }
});
