import { get } from './client'

export interface Article {
  id: string
  doi: string
  title: string
  authors: string[]
  abstract: string
  journal_id: string
  publish_date: string | null
  url: string
  fetched_at: string
}

export interface ArticlesResponse {
  articles: Article[]
}

export function getArticles(params?: { journal_id?: string; limit?: string; offset?: string }): Promise<ArticlesResponse> {
  return get<ArticlesResponse>('/articles', params as Record<string, string>)
}

export function getArticle(id: string): Promise<Article> {
  return get<Article>(`/articles/${id}`)
}

export function getMyFeed(params?: { limit?: string; offset?: string }): Promise<ArticlesResponse> {
  return get<ArticlesResponse>('/my/feed', params as Record<string, string>)
}
