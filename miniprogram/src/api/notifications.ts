import { get, buildQuery } from './client'

export interface Notification {
  id: string
  user_id: string
  article_id: string
  channel: string
  status: string
  error_message: string | null
  created_at: string
  sent_at: string | null
}

export function getNotifications(params: { limit?: number; offset?: number } = {}): Promise<{ notifications: Notification[] }> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/notifications${qs}`)
}
