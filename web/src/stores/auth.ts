import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, type AuthResponse } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<AuthResponse['user'] | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  function setAuth(res: AuthResponse) {
    token.value = res.token
    user.value = res.user
    localStorage.setItem('token', res.token)
    localStorage.setItem('user', JSON.stringify(res.user))
  }

  // Restore user profile (incl. is_admin) across reloads when token exists.
  try {
    const raw = localStorage.getItem('user')
    if (token.value && raw) {
      user.value = JSON.parse(raw) as AuthResponse['user']
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

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, isAdmin, login, register, logout }
})
