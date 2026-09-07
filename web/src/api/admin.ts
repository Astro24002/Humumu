import { get, post, put, del } from './client'
import type { Journal } from './journals'

export interface AdminStats {
  journal_count: number
  article_count: number
  user_count: number
  pending_requests: number
  pending_directory_reviews?: number
  cas_category_count?: number
}

export interface JournalRequest {
  id: string
  user_id: string
  journal_name: string
  source_url: string
  status: string
  created_at: string
  reviewed_at: string | null
}

export interface User {
  id: string
  email: string
  name: string
  push_frequency: string
  wechat_openid?: string | null
  wechat_template_subscribed?: boolean
  is_admin?: boolean
  created_at: string
  updated_at?: string | null
}

export function getStats(): Promise<AdminStats> {
  return get('/admin/stats')
}

export interface AdminJournalListParams {
  q?: string
  content_type?: string
  source_type?: string
  directory_status?: string
  sort?: 'name' | 'articles' | 'updated'
  limit?: number
  offset?: number
}

export function getAllJournals(
  params?: AdminJournalListParams,
): Promise<{ journals: Journal[]; total?: number }> {
  const qs = new URLSearchParams()
  if (params?.q) qs.set('q', params.q)
  if (params?.content_type) qs.set('content_type', params.content_type)
  if (params?.source_type) qs.set('source_type', params.source_type)
  if (params?.directory_status) qs.set('directory_status', params.directory_status)
  if (params?.sort) qs.set('sort', params.sort)
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  const suffix = qs.toString() ? `?${qs.toString()}` : ''
  return get(`/admin/journals${suffix}`)
}

export function createJournal(data: Partial<Journal>): Promise<void> {
  return post('/admin/journals', data)
}

export function updateJournal(id: string, data: Partial<Journal>): Promise<void> {
  return put(`/admin/journals/${id}`, data)
}

export function deleteJournal(id: string): Promise<void> {
  return del(`/admin/journals/${id}`)
}

export function setDirectoryStatus(id: string, directoryStatus: string): Promise<{ message: string }> {
  return post(`/admin/journals/${id}/directory_status`, { directory_status: directoryStatus })
}

export interface AdminRequestListParams {
  status?: string
  limit?: number
  offset?: number
}

export function getRequests(
  params?: AdminRequestListParams,
): Promise<{ requests: JournalRequest[]; total?: number }> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  const suffix = qs.toString() ? `?${qs.toString()}` : ''
  return get(`/admin/requests${suffix}`)
}

export function reviewRequest(id: string, status: string): Promise<void> {
  return put(`/admin/requests/${id}`, { status })
}

export interface AdminUserListParams {
  q?: string
  limit?: number
  offset?: number
}

export function getUsers(
  params?: AdminUserListParams,
): Promise<{ users: User[]; total?: number }> {
  const qs = new URLSearchParams()
  if (params?.q) qs.set('q', params.q)
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  const suffix = qs.toString() ? `?${qs.toString()}` : ''
  return get(`/admin/users${suffix}`)
}

export function setUserAdmin(userId: string, isAdmin: boolean): Promise<User> {
  return post(`/admin/users/${userId}/admin`, { is_admin: isAdmin })
}

export interface CasCategory {
  id: string
  year: number
  major: string
  minor: string
  zone: number
  is_top: boolean
}

export function createCasCategory(data: {
  year: number
  major: string
  minor: string
  zone: number
  is_top?: boolean
}): Promise<CasCategory> {
  return post('/admin/cas/categories', data)
}

export function attachCasCategories(journalId: string, categoryIds: string[]): Promise<{ message: string }> {
  return post(`/admin/journals/${journalId}/cas`, { category_ids: categoryIds })
}
