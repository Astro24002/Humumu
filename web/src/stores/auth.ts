import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getMe,
  login as apiLogin,
  register as apiRegister,
  type AuthResponse,
  type AuthUser,
} from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<AuthUser | null>(null)
  const bootstrapped = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  function withHasEmail(u: AuthUser, hasEmail?: boolean): AuthUser {
    const derived =
      typeof hasEmail === 'boolean'
        ? hasEmail
        : typeof u.has_email === 'boolean'
          ? u.has_email
          : !!(u.email && !u.email.endsWith('@wechat.user')) // keep inline to avoid circular util import in store bootstrap
    return {
      ...u,
      has_email: derived,
      // Old localStorage profiles may omit newer required flags.
      is_admin: !!u.is_admin,
      wechat_template_subscribed: !!u.wechat_template_subscribed,
      push_frequency: u.push_frequency || 'daily',
    }
  }

  function setUser(u: AuthUser, hasEmail?: boolean) {
    user.value = withHasEmail(u, hasEmail)
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  function setAuth(res: AuthResponse) {
    token.value = res.token
    setUser(res.user, res.has_email)
    localStorage.setItem('token', res.token)
  }

  // Restore cached profile immediately so first paint has name/is_admin.
  try {
    const raw = localStorage.getItem('user')
    if (token.value && raw) {
      user.value = withHasEmail(JSON.parse(raw) as AuthUser)
    }
  } catch {
    /* ignore corrupt cache */
  }

  async function login(email: string, password: string) {
    const res = await apiLogin(email, password)
    setAuth(res)
  }

  async function register(email: string, password: string, name: string) {
    const res = await apiRegister(email, password, name)
    setAuth(res)
  }

  async function refreshMe() {
    if (!token.value) {
      bootstrapped.value = true
      return
    }
    try {
      const res = await getMe()
      setUser(res.user, res.has_email)
    } catch {
      // Stale/invalid token — clear local session.
      logout()
    } finally {
      bootstrapped.value = true
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    bootstrapped,
    login,
    register,
    logout,
    refreshMe,
  }
})
