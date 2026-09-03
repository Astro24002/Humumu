import { get, post } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  description: string
  is_active: boolean
  created_at: string
  article_count: number
  last_article_date: string | null
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
}

export interface JournalListParams {
  q?: string
  content_type?: string
  major?: string
  minor?: string
  zone?: string
  top?: string
  year?: string
}

export function getJournals(params?: JournalListParams): Promise<JournalsResponse> {
  const cleaned: Record<string, string> = {}
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && String(v).trim() !== '') {
        cleaned[k] = String(v)
      }
    }
  }
  return get<JournalsResponse>('/journals', Object.keys(cleaned).length ? cleaned : undefined)
}

export function getJournal(id: string): Promise<Journal> {
  return get<Journal>(`/journals/${id}`)
}

export function requestJournal(journalName: string, sourceUrl: string): Promise<void> {
  return post('/journals/requests', { journal_name: journalName, source_url: sourceUrl })
}

export interface PreviewItem {
  title: string
  url: string
  published: string
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
