import { get, post } from './client'

export interface User {
  id: string
  email: string
  name: string
  wechat_openid: string
  push_frequency: string
  wechat_template_subscribed: boolean
  is_admin?: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  token: string
  user: User
  has_email: boolean
}

export function wechatLogin(code: string): Promise<AuthResponse> {
  return post('/auth/wechat', { code })
}

export function bindAccount(code: string, email: string, password: string): Promise<AuthResponse> {
  return post('/auth/bind-account', { code, email, password })
}

export function getMe(): Promise<{ user: User; has_email: boolean }> {
  return get('/auth/me')
}
