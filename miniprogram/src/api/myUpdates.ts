import { get, buildQuery } from './client'

export interface UpdateStatusFlags {
  is_read: boolean
  is_starred: boolean
  is_later: boolean
  original_clicked_at: string | null
}

export interface MyUpdateItem {
  article_id: string
  title: string
  authors: string[]
  abstract: string
  doi: string | null
  url: string
  original_url: string
  publish_date: string | null
  fetched_at: string | null
  journal_id: string
  journal_name: string
  content_type: string
  reasons: string[]
  status: UpdateStatusFlags
}

export interface MyUpdatesResponse {
  updates: MyUpdateItem[]
}

export function getMyUpdates(params: {
  limit?: number
  offset?: number
  filter?: string
} = {}): Promise<MyUpdatesResponse> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/my/updates${qs}`)
}
