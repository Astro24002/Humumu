import { get, post, put, del } from './client'
import type { Journal } from './journals'

export interface AdminStats {
  journal_count: number
  article_count: number
  user_count: number
  pending_requests: number
  pending_directory_reviews?: number
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
  is_admin?: boolean
  created_at: string
}

export function getStats(): Promise<AdminStats> {
  return get('/admin/stats')
}

export function getAllJournals(): Promise<{ journals: Journal[] }> {
  return get('/admin/journals')
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

export function getRequests(): Promise<{ requests: JournalRequest[] }> {
  return get('/admin/requests')
}

export function reviewRequest(id: string, status: string): Promise<void> {
  return put(`/admin/requests/${id}`, { status })
}

export function getUsers(): Promise<{ users: User[] }> {
  return get('/admin/users')
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
