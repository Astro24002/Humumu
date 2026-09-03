/** YYYY-MM-DD from ISO or date-like string. */
export function formatDate(d?: string | null): string {
  if (!d) return ''
  return d.slice(0, 10)
}

/** Compact local datetime: YYYY-MM-DD HH:mm */
export function formatDateTime(d?: string | null): string {
  if (!d) return ''
  const s = d.trim()
  if (!s) return ''
  // Prefer parsing so Z/offset convert to local wall clock when possible
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
  // Fallback: strip seconds/fraction and T
  return s.replace('T', ' ').replace(/\.\d+/, '').replace(/Z$/, '').slice(0, 16)
}
