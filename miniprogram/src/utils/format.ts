export function formatDate(d: string): string {
  if (!d) return ''
  return d.slice(0, 10)
}

/** Compact local datetime: YYYY-MM-DD HH:mm */
export function formatDateTime(d?: string | null): string {
  if (!d) return ''
  const s = String(d).trim()
  if (!s) return ''
  const t = Date.parse(s)
  if (!Number.isNaN(t)) {
    const dt = new Date(t)
    const y = dt.getFullYear()
    const m = String(dt.getMonth() + 1).padStart(2, '0')
    const day = String(dt.getDate()).padStart(2, '0')
    const hh = String(dt.getHours()).padStart(2, '0')
    const mm = String(dt.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${day} ${hh}:${mm}`
  }
  return s.replace('T', ' ').replace(/\.\d+/, '').replace(/Z$/, '').slice(0, 16)
}

/** Compact host+path label for display; keeps full URL for actions. */
export function shortUrl(url: string, max = 40): string {
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
export function doiUrl(doi: string): string {
  if (!doi) return ''
  const s = String(doi).trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s)) return s
  return `https://doi.org/${s.replace(/^doi:\s*/i, '')}`
}

export function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max) + '...'
}

export function timeAgo(d: string): string {
  const diff = Date.now() - new Date(d).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}
