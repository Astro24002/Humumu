import { get, buildQuery } from './client'

export interface Notification {
  id: string
  user_id: string
  article_id: string
  channel: string
  status: string
  error_message: string | null
  match_reasons?: string[]
  created_at: string
  sent_at: string | null
  article_title?: string | null
}

export function getNotifications(params: {
  limit?: number
  offset?: number
  status?: string
  channel?: string
} = {}): Promise<{ notifications: Notification[]; total: number }> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/notifications${qs}`)
}
