import { get } from './client'

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
}

export interface JournalsResponse {
  journals: Journal[]
}

export interface JournalResponse {
  journal: Journal
}

export function getJournals(): Promise<JournalsResponse> {
  return get('/journals')
}

export function getJournal(id: string): Promise<JournalResponse> {
  return get(`/journals/${id}`)
}
