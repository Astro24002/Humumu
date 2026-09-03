import { get, buildQuery } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  description: string
  fetch_interval: number
  is_active: boolean
  created_by: string | null
  created_at: string
  article_count: number
  last_article_date: string | null
  content_type?: string
  directory_status?: string
  homepage_url?: string
}

export interface JournalsResponse {
  journals: Journal[]
}

export interface JournalListParams {
  q?: string
  content_type?: string
  major?: string
  minor?: string
  zone?: string | number
  top?: string
  year?: string | number
}

export function getJournals(params: JournalListParams = {}): Promise<JournalsResponse> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/journals${qs}`)
}

export function getJournal(id: string): Promise<Journal> {
  return get(`/journals/${id}`)
}
