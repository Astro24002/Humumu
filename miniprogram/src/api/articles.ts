import { get } from './client'

export interface Article {
  id: string
  doi: string
  title: string
  authors: string[]
  abstract: string
  journal_id: string
  journal_name: string
  journal_source_type: string
  publish_date: string | null
  url: string
  fetched_at: string
}

export interface ArticlesResponse {
  articles: Article[]
  total: number
}

export function getArticles(params: { limit?: number; offset?: number; journal_id?: string } = {}): Promise<ArticlesResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.journal_id) query.set('journal_id', params.journal_id)
  const qs = query.toString()
  return get(`/articles${qs ? '?' + qs : ''}`)
}

export function getArticle(id: string): Promise<{ article: Article }> {
  return get(`/articles/${id}`)
}

export function getMyFeed(params: { limit?: number; offset?: number } = {}): Promise<ArticlesResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  const qs = query.toString()
  return get(`/my/feed${qs ? '?' + qs : ''}`)
}
