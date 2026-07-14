import { useAuthStore } from '@/stores/auth'

const BASE_URL = 'http://localhost:8080/api/v1'

// Mini program doesn't support URLSearchParams
export function buildQuery(params: Record<string, string | number | undefined>): string {
  const parts: string[] = []
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') {
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    }
  }
  return parts.length ? '?' + parts.join('&') : ''
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const auth = useAuthStore()
  const header: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (auth.token) {
    header['Authorization'] = `Bearer ${auth.token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + path,
      method: opts.method || 'GET',
      data: opts.data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else if (res.statusCode === 401) {
          auth.logout()
          reject(new Error('登录已过期'))
        } else {
          const data = res.data as any
          reject(new Error(data?.error || '请求失败'))
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络错误'))
      },
    })
  })
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

export function post<T>(path: string, data?: any): Promise<T> {
  return request<T>(path, { method: 'POST', data })
}

export function put<T>(path: string, data?: any): Promise<T> {
  return request<T>(path, { method: 'PUT', data })
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}
