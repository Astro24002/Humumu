import { post } from './client'

export interface AuthResponse {
  token: string
  user: {
    id: string
    email: string
    name: string
    wechat_openid?: string
    push_frequency: string
    created_at: string
  }
}

export function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/register', { email, password, name })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/login', { email, password })
}
