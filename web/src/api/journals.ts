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
}

export interface JournalsResponse {
  journals: Journal[]
}

export function getJournals(): Promise<JournalsResponse> {
  return get<JournalsResponse>('/journals')
}

export function getJournal(id: string): Promise<Journal> {
  return get<Journal>(`/journals/${id}`)
}

export function requestJournal(journalName: string, sourceUrl: string): Promise<void> {
  return post('/journals/requests', { journal_name: journalName, source_url: sourceUrl })
}

export interface PreviewResult {
  name: string
  source_type: string
}

export function previewJournal(url: string): Promise<PreviewResult> {
  return post('/my/journals/preview', { source_url: url })
}

export function addMyJournal(name: string, sourceUrl: string): Promise<{ journal: Journal; already_existed: boolean }> {
  return post('/my/journals', { name, source_url: sourceUrl })
}
