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

export function getCasCategories(): Promise<CasCategoriesResponse> {
  return get<CasCategoriesResponse>('/categories/cas')
}
