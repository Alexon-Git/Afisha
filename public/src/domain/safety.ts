export function externalUrl(value: string | null | undefined): string | null {
  if (!value || !/^https?:\/\//.test(value) || /[\s\\\u0000-\u001f\u007f]/.test(value)) return null;
  try {
    const url = new URL(value);
    if (!/^https?:$/.test(url.protocol) || url.username || url.password) return null;
    return url.href;
  } catch { return null; }
}

export function imagePath(value: string | null): string | null {
  if (!value || /[\u0000-\u0020\u007f\\]/.test(value)) return null;
  // Query/fragment variants refer to the same local file. Never forward their
  // contents or decode the physical path when constructing an image URL.
  const path = value.split(/[?#]/, 1)[0];
  return /^\/static\/uploads\/[a-f0-9]{32}\.(jpg|png|webp)$/.test(path) ? path : null;
}

export function siteOrigin(value = process.env.SITE_URL): string | null {
  const safe = externalUrl(value);
  if (!safe || !value) return null;
  const url = new URL(safe);
  if (url.pathname !== '/' || url.search || url.hash) return null;
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (local) return process.env.ALLOW_LOCAL_SITE_URL === '1' ? url.origin : null;
  if (url.protocol !== 'https:' || !url.hostname.includes('.') || url.hostname.endsWith('.invalid')) return null;
  return url.origin;
}
