import { get, post, buildQuery } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  description?: string
  fetch_interval?: number
  is_active?: boolean
  created_by?: string | null
  created_at: string
  article_count?: number | null
  last_article_date?: string | null
  content_type?: string
  directory_status?: string
  homepage_url?: string
  consecutive_failures?: number
  last_error?: string | null
  last_success_at?: string | null
  health_status?: string | null
}

export interface JournalsResponse {
  journals: Journal[]
  total?: number
}

export interface JournalListParams {
  q?: string
  content_type?: string
  source_type?: string
  major?: string
  minor?: string
  zone?: string | number
  top?: string
  year?: string | number
  sort?: string
  limit?: string | number
  offset?: string | number
}

export function getJournals(params: JournalListParams = {}): Promise<JournalsResponse> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/journals${qs}`)
}

export function getJournal(id: string): Promise<Journal> {
  return get(`/journals/${id}`)
}

export interface PreviewItem {
  title: string
  url: string
  published?: string | null
}

export interface PreviewResult {
  name: string
  source_type: string
  items: PreviewItem[]
}

export function previewJournal(url: string): Promise<PreviewResult> {
  return post('/my/journals/preview', { source_url: url })
}

export function addMyJournal(
  name: string,
  sourceUrl: string,
  visibility: 'private' | 'apply_public' = 'private',
): Promise<{ journal: Journal; already_existed: boolean }> {
  return post('/my/journals', { name, source_url: sourceUrl, visibility })
}
