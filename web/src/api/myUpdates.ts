import { get } from './client'

export interface UpdateStatusFlags {
  is_read: boolean
  is_starred: boolean
  is_later: boolean
  original_clicked_at: string | null
}

export interface MyUpdateItem {
  article_id: string
  title: string
  authors?: string[]
  abstract?: string
  doi?: string | null
  url?: string
  original_url?: string
  publish_date?: string | null
  fetched_at?: string | null
  journal_id: string
  journal_name: string
  journal_source_type?: string | null
  content_type: string
  reasons?: string[]
  status: UpdateStatusFlags
}

export interface MyUpdatesResponse {
  updates: MyUpdateItem[]
  total: number
}

export function getMyUpdates(params?: {
  limit?: string
  offset?: string
  filter?: string
}): Promise<MyUpdatesResponse> {
  return get<MyUpdatesResponse>('/my/updates', params as Record<string, string> | undefined)
}
