/** Compact host+path label for display; keeps full URL for hrefs. */
export function shortUrl(url?: string | null, max = 48): string {
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

/** Normalize bare DOI to https://doi.org/...; pass through full URLs. */
export function doiUrl(doi?: string | null): string {
  if (!doi) return ''
  const s = String(doi).trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s)) return s
  return `https://doi.org/${s.replace(/^doi:\s*/i, '')}`
}

/** Only allow same-app relative paths as post-login redirects (block open redirects). */
export function safeRedirect(raw: unknown, fallback = '/my'): string {
  if (raw == null) return fallback
  const s = String(raw).trim()
  if (!s) return fallback
  // Must be a relative path starting with single /
  if (!s.startsWith('/') || s.startsWith('//')) return fallback
  if (s.startsWith('/\\')) return fallback
  // Reject protocol-like and external
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(s)) return fallback
  // Avoid bouncing back to auth pages
  if (s === '/login' || s === '/register' || s.startsWith('/login?') || s.startsWith('/register?')) {
    return fallback
  }
  return s
}
