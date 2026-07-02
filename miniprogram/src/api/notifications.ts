import { get } from './client'

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
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  const qs = query.toString()
  return get(`/notifications${qs ? '?' + qs : ''}`)
}
