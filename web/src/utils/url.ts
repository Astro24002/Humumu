/** Compact host+path label for display; keeps full URL for hrefs. */
export function shortUrl(url: string, max = 48): string {
  if (!url) return ''
  try {
    const u = new URL(url)
    const path = u.pathname === '/' ? '' : u.pathname
    const full = `${u.host}${path}`
    return full.length > max ? `${full.slice(0, max)}…` : full
  } catch {
    return url.length > max ? `${url.slice(0, max)}…` : url
  }
}
