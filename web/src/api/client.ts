const BASE_URL = '/api/v1'

interface ApiError {
  error: string
}

export class ApiClientError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText })) as ApiError
    // Drop stale session on unauthorized so guards bounce to login.
    if (res.status === 401 && token && !path.startsWith('/auth/login') && !path.startsWith('/auth/register')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Soft reload of auth store if pinia is already up (avoid hard circular import).
      try {
        const { useAuthStore } = await import('@/stores/auth')
        useAuthStore().logout()
      } catch {
        // ignore — localStorage already cleared
      }
    }
    throw new ApiClientError(res.status, body.error || (res.status === 401 ? '登录已过期' : 'request failed'))
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return {} as T
  }
  return res.json()
}

export function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return request<T>(path + qs)
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined })
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined })
}
