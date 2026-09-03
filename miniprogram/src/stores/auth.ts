import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMe } from '@/api/auth'

interface User {
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

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const hasEmail = computed(() => user.value?.email ? !user.value.email.endsWith('@wechat.user') : false)

  function save(t: string, u: User) {
    token.value = t
    user.value = u
    uni.setStorageSync('token', t)
    uni.setStorageSync('user', JSON.stringify(u))
  }

  function restore() {
    const t = uni.getStorageSync('token')
    const u = uni.getStorageSync('user')
    if (t && u) {
      token.value = t as string
      user.value = JSON.parse(u as string) as User
    }
  }

  async function refreshMe() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = res.user
      uni.setStorageSync('user', JSON.stringify(res.user))
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    uni.removeStorageSync('token')
    uni.removeStorageSync('user')
    uni.reLaunch({ url: '/pages/index/index' })
  }

  return { token, user, isLoggedIn, hasEmail, save, restore, refreshMe, logout }
})
