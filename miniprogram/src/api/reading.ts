import { get, put, post } from './client'

export interface ArticleStatus {
  user_id: string
  article_id: string
  is_read: boolean
  is_starred: boolean
  is_later: boolean
  original_clicked_at: string | null
  updated_at?: string | null
}

export function getArticleStatus(articleId: string): Promise<ArticleStatus> {
  return get(`/my/articles/${articleId}/status`)
}

export function updateArticleStatus(
  articleId: string,
  body: { is_read?: boolean; is_starred?: boolean; is_later?: boolean },
): Promise<ArticleStatus> {
  return put(`/my/articles/${articleId}/status`, body)
}

export function recordOriginalClick(articleId: string): Promise<ArticleStatus> {
  return post(`/my/articles/${articleId}/original-click`)
}
