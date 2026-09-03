import { get } from './client'

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

export function getNotifications(params?: {
  limit?: string
  offset?: string
  status?: string
}): Promise<{ notifications: Notification[] }> {
  return get('/notifications', params as Record<string, string>)
}
