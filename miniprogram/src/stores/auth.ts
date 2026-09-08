import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { bindEmail as apiBindEmail, getMe, type User } from '@/api/auth'
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
    return {
      ...u,
      has_email: derived,
      // Old storage profiles may omit newer required flags.
      is_admin: !!u.is_admin,
      wechat_template_subscribed: !!u.wechat_template_subscribed,
      push_frequency: u.push_frequency || 'daily',
    }
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

  /** Attach email+password to current WeChat stub; rotates token. */
  async function bindEmail(email: string, password: string) {
    const res = await apiBindEmail(email, password)
    save(res.token, res.user, res.has_email)
  }

  function logout() {
    token.value = ''
    user.value = null
    uni.removeStorageSync('token')
    uni.removeStorageSync('user')
    uni.reLaunch({ url: '/pages/index/index' })
  }

  return { token, user, isLoggedIn, hasEmail, save, restore, refreshMe, bindEmail, logout }
})
