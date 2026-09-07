import { get } from './client'

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
  total: number
}

export function getArticles(params?: {
  journal_id?: string
  content_type?: string
  source_type?: string
  limit?: string
  offset?: string
}): Promise<ArticlesResponse> {
  return get<ArticlesResponse>('/articles', params as Record<string, string>)
}

export function getArticle(id: string): Promise<Article> {
  return get<Article>(`/articles/${id}`)
}
