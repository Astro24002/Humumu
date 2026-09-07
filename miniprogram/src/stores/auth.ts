import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMe, type User } from '@/api/auth'
import { isWechatPlaceholderEmail } from '@/utils/format'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const hasEmail = computed(() => {
    const u = user.value
    if (!u) return false
    if (typeof u.has_email === 'boolean') return u.has_email
    return !!(u.email && !isWechatPlaceholderEmail(u.email))
  })

  function withHasEmail(u: User, hasEmailFlag?: boolean): User {
    const derived =
      typeof hasEmailFlag === 'boolean'
        ? hasEmailFlag
        : typeof u.has_email === 'boolean'
          ? u.has_email
          : !!(u.email && !isWechatPlaceholderEmail(u.email))
    return { ...u, has_email: derived }
  }

  function save(t: string, u: User, hasEmailFlag?: boolean) {
    token.value = t
    user.value = withHasEmail(u, hasEmailFlag)
    uni.setStorageSync('token', t)
    uni.setStorageSync('user', JSON.stringify(user.value))
  }

  function restore() {
    const t = uni.getStorageSync('token')
    const u = uni.getStorageSync('user')
    if (t && u) {
      token.value = t as string
      try {
        user.value = withHasEmail(JSON.parse(u as string) as User)
      } catch {
        user.value = null
      }
    }
  }

  async function refreshMe() {
    if (!token.value) return
    try {
      const res = await getMe()
      user.value = withHasEmail(res.user, res.has_email)
      uni.setStorageSync('user', JSON.stringify(user.value))
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
