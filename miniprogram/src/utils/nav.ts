/** Tab bar page paths (no leading slash). */
export const TAB_PAGES = new Set([
  'pages/index/index',
  'pages/journals/index',
  'pages/subscriptions/index',
  'pages/profile/index',
])

/** Build current page path+query for login return-to. */
export function currentPageFrom(): string {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1] as any
  if (!cur) return ''
  const route = String(cur.route || '').replace(/^\/+/, '')
  const opts = cur.options || {}
  const qs = Object.keys(opts)
    .filter((k) => opts[k] != null && opts[k] !== '')
    .map((k) => `${k}=${encodeURIComponent(String(opts[k]))}`)
    .join('&')
  const fullPath = cur.$page && cur.$page.fullPath
    ? String(cur.$page.fullPath).replace(/^\/+/, '')
    : ''
  let from = ''
  if (fullPath) {
    from = fullPath.startsWith('pages/') ? fullPath : `pages/${fullPath}`
  } else if (route) {
    const base = route.startsWith('pages/') ? route : `pages/${route}`
    from = qs ? `${base}?${qs}` : base
  }
  if (from.startsWith('pages/login')) return ''
  return from
}

/** Navigate to login, carrying optional return path. */
export function goLogin(from?: string) {
  const target = from != null ? from : currentPageFrom()
  const q = target ? `?from=${encodeURIComponent(target)}` : ''
  uni.navigateTo({ url: `/pages/login/index${q}` })
}
