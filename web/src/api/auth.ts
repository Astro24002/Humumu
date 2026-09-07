import { get, post } from './client'

export interface AuthUser {
  id: string
  email: string
  name: string
  wechat_openid?: string | null
  push_frequency: string
  wechat_template_subscribed?: boolean
  is_admin?: boolean
  created_at: string
  updated_at?: string | null
  /** Client-side: true email (not synthetic @wechat.user). Set from /auth/me or login. */
  has_email?: boolean
}

export interface AuthResponse {
  token: string
  user: AuthUser
  has_email?: boolean
}

export interface MeResponse {
  user: AuthUser
  has_email: boolean
}

export function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/register', { email, password, name })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/login', { email, password })
}

export function getMe(): Promise<MeResponse> {
  return get<MeResponse>('/auth/me')
}
