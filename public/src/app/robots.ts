import type { MetadataRoute } from 'next';
import { siteOrigin } from '../domain/safety';

export const dynamic = 'force-dynamic';
export default function robots(): MetadataRoute.Robots {
  const origin = siteOrigin();
  return origin ? { rules: { userAgent: '*', allow: '/' }, sitemap: `${origin}/sitemap.xml` }
    : { rules: { userAgent: '*', disallow: '/' } };
}
