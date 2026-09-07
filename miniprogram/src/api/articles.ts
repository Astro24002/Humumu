import { get, buildQuery } from './client'

export interface Article {
  id: string
  doi?: string | null
  title: string
  authors: string[]
  abstract?: string
  journal_id: string
  journal_name?: string | null
  journal_source_type?: string | null
  content_type?: string
  publish_date?: string | null
  url?: string
  fetched_at: string
}

export interface ArticlesResponse {
  articles: Article[]
  total?: number
}

export function getArticles(params: {
  limit?: number
  offset?: number
  journal_id?: string
  content_type?: string
  source_type?: string
} = {}): Promise<ArticlesResponse> {
  const qs = buildQuery(params as Record<string, string | number | undefined>)
  return get(`/articles${qs}`)
}

export function getArticle(id: string): Promise<Article> {
  return get(`/articles/${id}`)
}
