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
