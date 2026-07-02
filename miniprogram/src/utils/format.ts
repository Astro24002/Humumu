export function formatDate(d: string): string {
  if (!d) return ''
  return d.slice(0, 10)
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
