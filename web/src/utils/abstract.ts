/** Strip common arXiv announce prefixes from feed abstracts. */
export function cleanAbstract(text?: string | null): string {
  if (!text) return ''
  return text.replace(/^arXiv:\S+ Announce Type: \S+\s*\n\s*Abstract:\s*/i, '')
}

export function truncateAbstract(text?: string | null, max = 200): string {
  const cleaned = cleanAbstract(text)
  return cleaned.length > max ? cleaned.slice(0, max) + '…' : cleaned
}
