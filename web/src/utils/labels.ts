/** Human label for match reason codes from my-updates / notifications. */
export function reasonLabel(r: string): string {
  const map: Record<string, string> = {
    journal: '期刊',
    author: '作者',
    keyword: '关键词',
  }
  return map[r] || r
}

/** Compact author list: "A, B, C 等" when longer than max. */
export function formatAuthors(authors?: string[] | null, max = 3): string {
  const list = (authors || []).filter(Boolean)
  if (!list.length) return ''
  const head = list.slice(0, max).join(', ')
  return list.length > max ? `${head} 等` : head
}

/** Directory visibility label for journals. */
export function dirStatusLabel(s?: string | null): string {
  const map: Record<string, string> = {
    public: '公开',
    private: '私有',
    pending_review: '待审公开',
    rejected: '公开未通过',
    hidden: '已下架',
  }
  return map[s || ''] || s || ''
}

/** Naive tag type for directory status. */
export function dirStatusType(s?: string | null): 'default' | 'warning' | 'error' | 'info' | 'success' {
  if (s === 'pending_review') return 'warning'
  if (s === 'rejected' || s === 'hidden') return 'error'
  if (s === 'private') return 'info'
  if (s === 'public') return 'success'
  return 'default'
}

/** Notification delivery status label. */
export function notifStatusLabel(s?: string | null): string {
  switch (s) {
    case 'sent': return '已发送'
    case 'pending': return '等待中'
    case 'failed': return '失败'
    default: return s || ''
  }
}

/** Naive tag type for notification delivery status. */
export function notifStatusTagType(s?: string | null): 'success' | 'error' | 'warning' | 'default' {
  if (s === 'sent') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'pending') return 'warning'
  return 'default'
}

/** Push frequency label (subscription override or global). */
export function freqLabel(f?: string | null): string {
  if (f === 'realtime') return '实时'
  if (f === 'daily') return '每日'
  return '跟随全局'
}

/** content_type display: journal/preprint. */
export function contentTypeLabel(t?: string | null): string {
  if (t === 'preprint') return '预印本'
  if (t === 'journal') return '期刊'
  return t || ''
}

/** Journal/article source_type display. */
export function sourceTypeLabel(t?: string | null): string {
  if (!t) return ''
  if (t === 'arxiv') return 'arXiv'
  if (t === 'rss') return 'RSS'
  if (t === 'cnki') return '知网'
  return t
}

/** Naive tag type for source_type badges. */
export function sourceTypeTagType(t?: string | null): 'info' | 'success' | 'default' {
  if (t === 'arxiv') return 'info'
  if (t === 'rss' || t === 'cnki') return 'success'
  return 'default'
}

/** Fetch health label for journals. */
export function healthStatusLabel(s?: string | null): string {
  if (s === 'paused') return '抓取暂停'
  if (s === 'ok' || s === 'healthy') return '正常'
  return s || ''
}

/** Notification / push channel label. */
export function channelLabel(c?: string | null): string {
  if (c === 'email') return '邮件'
  if (c === 'wechat') return '微信'
  return c || ''
}

/** Naive tag type for notification / push channel. */
export function channelTagType(c?: string | null): 'primary' | 'success' | 'default' {
  if (c === 'email') return 'primary'
  if (c === 'wechat') return 'success'
  return 'default'
}

/** Journal-request review status label (admin / user request queues). */
export function requestStatusLabel(s?: string | null): string {
  if (s === 'pending') return '待审批'
  if (s === 'approved') return '已通过'
  if (s === 'rejected') return '已拒绝'
  return s || ''
}

/** Naive tag type for journal-request review status. */
export function requestStatusTagType(s?: string | null): 'success' | 'error' | 'warning' | 'default' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'error'
  if (s === 'pending') return 'warning'
  return 'default'
}

/** Synthetic email assigned to WeChat-only accounts (not a real inbox). */
export function isWechatPlaceholderEmail(email?: string | null): boolean {
  return !!email && email.endsWith('@wechat.user')
}

