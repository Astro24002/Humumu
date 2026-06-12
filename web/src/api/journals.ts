import { get, post } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  is_active: boolean
  created_at: string
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
