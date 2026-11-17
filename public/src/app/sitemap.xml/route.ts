import { getPublishedEvents } from '../../api/server';
import { siteOrigin } from '../../domain/safety';

export const dynamic = 'force-dynamic';
const headers = { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'no-store' };
const escapeXml = (value: string) => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

export async function GET() {
  const origin = siteOrigin();
  if (!origin) return new Response('<error>SITE_URL required</error>', { status: 503, headers });
  try {
    const urls = new Set([`${origin}/`, `${origin}/events`]);
    let totalPages = 1;
    for (let page = 1; page <= totalPages; page++) {
      const result = await getPublishedEvents(page, 100);
      if (!Number.isInteger(result.total_pages) || result.total_pages < 0 || result.total_pages > 499 ||
          result.page !== page || (page > 1 && result.total_pages !== totalPages)) throw new Error();
      totalPages = result.total_pages;
      for (const event of result.items) {
        if (event.publication_status === 'published' && Number.isSafeInteger(event.id) && event.id > 0) urls.add(`${origin}/events/${event.id}`);
      }
    }
    const xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
      [...urls].map(url => `<url><loc>${escapeXml(url)}</loc></url>`).join('') + '</urlset>';
    return new Response(xml, { headers });
  } catch { return new Response('<error>Temporarily unavailable</error>', { status: 503, headers }); }
}
