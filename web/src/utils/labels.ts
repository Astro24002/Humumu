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
