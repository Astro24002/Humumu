import { get, post, put, del, patch } from './client'
import type { Journal } from './journals'

export interface AuthorTracking {
  id: string
  user_id: string
  author_name: string
  created_at: string
}

export interface KeywordSubscription {
  id: string
  user_id: string
  keyword: string
  created_at: string
}

export interface SubscribedJournal extends Journal {
  push_frequency?: string
  email_enabled?: boolean
  wechat_enabled?: boolean
}

export interface JournalSubscriptionPrefs {
  user_id: string
  journal_id: string
  created_at: string
  push_frequency: string
  email_enabled: boolean
  wechat_enabled: boolean
}

export function getSubscribedJournals(): Promise<{ journals: SubscribedJournal[] }> {
  return get('/subscriptions/journals')
}

export function subscribeJournal(id: string): Promise<void> {
  return post(`/subscriptions/journals/${id}`)
}

export function unsubscribeJournal(id: string): Promise<void> {
  return del(`/subscriptions/journals/${id}`)
}

export function updateJournalSubscriptionPrefs(
  journalId: string,
  prefs: {
    push_frequency?: string
    email_enabled?: boolean
    wechat_enabled?: boolean
  },
): Promise<JournalSubscriptionPrefs> {
  return patch(`/subscriptions/journals/${journalId}`, prefs)
}

export function getAuthors(): Promise<{ authors: AuthorTracking[] }> {
  return get('/subscriptions/authors')
}

export function addAuthor(authorName: string): Promise<void> {
  return post('/subscriptions/authors', { author_name: authorName })
}

export function removeAuthor(id: string): Promise<void> {
  return del(`/subscriptions/authors/${id}`)
}

export function getKeywords(): Promise<{ keywords: KeywordSubscription[] }> {
  return get('/subscriptions/keywords')
}

export function addKeyword(keyword: string): Promise<void> {
  return post('/subscriptions/keywords', { keyword })
}

export function removeKeyword(id: string): Promise<void> {
  return del(`/subscriptions/keywords/${id}`)
}

export function updatePushFrequency(freq: string): Promise<void> {
  return put('/settings/push-frequency', { push_frequency: freq })
}
