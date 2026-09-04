import { get } from './client'

export interface CasCategory {
  id: string
  year: number
  major: string
  minor: string
  zone: number
  is_top: boolean
}

export interface CasCategoriesResponse {
  categories: CasCategory[]
  years: number[]
}

export function getCasCategories(params?: {
  year?: number
  major?: string
}): Promise<CasCategoriesResponse> {
  const qs: Record<string, string> = {}
  if (params?.year != null) qs.year = String(params.year)
  if (params?.major) qs.major = params.major
  return get<CasCategoriesResponse>('/categories/cas', Object.keys(qs).length ? qs : undefined)
}
