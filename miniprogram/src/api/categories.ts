import { get, buildQuery } from './client'

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
  const qs = buildQuery({
    year: params?.year,
    major: params?.major,
  } as Record<string, string | number | undefined>)
  return get(`/categories/cas${qs}`)
}
