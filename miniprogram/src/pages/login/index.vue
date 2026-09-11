<template>
  <view class="login-container">
    <view class="logo">
      <text class="logo-text">Humumu</text>
      <text class="logo-desc">关注最新学术动态</text>
    </view>

    <!-- Bind email onto current WeChat stub (legacy / already logged in) -->
    <view v-if="needsBind">
      <view class="bind-hint">{{
        bindMode === 'merge'
          ? '用已有邮箱账号登录，将当前微信挂到该账号'
          : '为当前微信账号设置邮箱与密码，用于邮件推送与网页登录'
      }}</view>
      <uni-forms ref="formRef" :model="form">
        <uni-forms-item label="邮箱" name="email">
          <uni-easyinput
            v-model="form.email"
            placeholder="请输入邮箱"
            type="email"
            :disabled="loading"
          />
        </uni-forms-item>
        <uni-forms-item label="密码" name="password">
          <uni-easyinput
            v-model="form.password"
            :placeholder="bindMode === 'merge' ? '邮箱账号密码' : '设置密码（至少6位）'"
            type="password"
            :disabled="loading"
          />
        </uni-forms-item>
      </uni-forms>
      <button class="btn-primary" :loading="loading" :disabled="loading" @click="handleBind">
        {{ bindMode === 'merge' ? '绑定到已有邮箱' : '绑定邮箱' }}
      </button>
      <button
        class="btn-text"
        :disabled="loading"
        @click="toggleBindMode"
      >
        {{ bindMode === 'merge' ? '改为给当前微信设邮箱' : '已有邮箱账号？合并绑定' }}
      </button>
      <button class="btn-text" :disabled="loading" @click="skipBind">跳过，直接使用</button>
    </view>

    <!-- Email-first: bind WeChat onto an existing email account -->
    <view v-else>
      <view class="bind-hint">请用网页注册的邮箱登录，将微信绑定到该账号。</view>
      <uni-forms :model="form">
        <uni-forms-item label="邮箱" name="email">
          <uni-easyinput
            v-model="form.email"
            placeholder="注册邮箱"
            type="email"
            :disabled="loading"
          />
        </uni-forms-item>
        <uni-forms-item label="密码" name="password">
          <uni-easyinput
            v-model="form.password"
            placeholder="邮箱账号密码"
            type="password"
            :disabled="loading"
          />
        </uni-forms-item>
      </uni-forms>
      <button class="btn-primary" :loading="loading" :disabled="loading" @click="handleEmailBind">
        邮箱登录并绑定微信
      </button>
      <button class="btn-text" :loading="loading" :disabled="loading" @click="handleWeChatLogin">
        没有邮箱？微信一键登录
      </button>
    </view>

    <view v-if="error" class="error-msg">{{ error }}</view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { wechatLogin, bindAccount } from '@/api/auth'
import { TAB_PAGES } from '@/utils/nav'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const needsBind = ref(false)
/** merge = bind-account onto existing email; email = attach to current stub */
const bindMode = ref<'email' | 'merge'>('merge')
const wxCode = ref('')
const form = ref({ email: '', password: '' })
/** Optional return path (no leading slash), e.g. pages/article/detail?id=... */
const returnTo = ref('')

function normalizePath(raw?: string | null): string {
  if (!raw) return ''
  let s = String(raw).trim()
  if (!s) return ''
  try {
    s = decodeURIComponent(s)
  } catch {
    /* keep raw */
  }
  s = s.replace(/^\/+/, '')
  if (s.startsWith('pages/login')) return ''
  return s
}

function pathOnly(full: string): string {
  return full.split('?')[0]
}

function goAfterLogin() {
  const target = normalizePath(returnTo.value)
  if (target) {
    const base = pathOnly(target)
    if (TAB_PAGES.has(base)) {
      uni.switchTab({ url: `/${base}` })
      return
    }
    uni.redirectTo({
      url: `/${target}`,
      fail: () => uni.switchTab({ url: '/pages/index/index' }),
    })
    return
  }
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack({
      fail: () => uni.switchTab({ url: '/pages/index/index' }),
    })
    return
  }
  uni.switchTab({ url: '/pages/index/index' })
}

async function ensureWxCode() {
  if (wxCode.value) return wxCode.value
  const { code } = await uni.login()
  wxCode.value = code
  return code
}

function toggleBindMode() {
  if (loading.value) return
  bindMode.value = bindMode.value === 'email' ? 'merge' : 'email'
  error.value = ''
}

onMounted(async () => {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1] as any
  const q = (cur && cur.options) || {}
  returnTo.value = normalizePath(q.from || q.redirect || '')
  const mode = typeof q.mode === 'string' ? q.mode : ''
  // Profile "去绑定" deep-link: logged-in wechat user without email.
  if (mode === 'bind' && auth.isLoggedIn && !auth.hasEmail) {
    needsBind.value = true
    bindMode.value = 'merge'
    return
  }
  // Email account already logged in but WeChat not linked: stay on email-bind form.
  if (mode === 'bind-wechat') {
    needsBind.value = false
    if (auth.hasEmail && auth.user?.email) {
      form.value.email = auth.user.email
    }
    return
  }
  if (auth.isLoggedIn) {
    goAfterLogin()
  }
})

async function handleEmailBind() {
  if (loading.value) return
  if (!form.value.email || !form.value.password) {
    error.value = '请填写邮箱和密码'
    return
  }
  if (form.value.password.length < 6) {
    error.value = '密码至少6位'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await ensureWxCode()
    const res = await bindAccount(wxCode.value, form.value.email.trim(), form.value.password)
    auth.save(res.token, res.user, res.has_email)
    goAfterLogin()
  } catch (e: any) {
    error.value = e.message || '绑定失败'
  } finally {
    loading.value = false
  }
}

async function handleWeChatLogin() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    await ensureWxCode()
    const res = await wechatLogin(wxCode.value)
    auth.save(res.token, res.user, res.has_email)
    if (!res.has_email) {
      needsBind.value = true
      bindMode.value = 'merge'
    } else {
      goAfterLogin()
    }
  } catch (e: any) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleBind() {
  if (loading.value) return
  if (!form.value.email || !form.value.password) {
    error.value = '请填写邮箱和密码'
    return
  }
  if (form.value.password.length < 6) {
    error.value = '密码至少6位'
    return
  }
  loading.value = true
  error.value = ''
  try {
    if (bindMode.value === 'email') {
      await auth.bindEmail(form.value.email.trim(), form.value.password)
    } else {
      await ensureWxCode()
      const res = await bindAccount(wxCode.value, form.value.email.trim(), form.value.password)
      auth.save(res.token, res.user, res.has_email)
    }
    goAfterLogin()
  } catch (e: any) {
    error.value = e.message || '绑定失败'
  } finally {
    loading.value = false
  }
}

function skipBind() {
  if (loading.value) return
  goAfterLogin()
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 40rpx;
}
.logo { text-align: center; margin-bottom: 60rpx; }
.logo-text { font-size: 48rpx; font-weight: bold; color: #333; }
.logo-desc { font-size: 28rpx; color: #999; margin-top: 16rpx; display: block; }
.btn-primary {
  width: 100%;
  padding: 24rpx;
  background: #3cc51f;
  color: #fff;
  border: none;
  border-radius: 12rpx;
  font-size: 32rpx;
  margin-top: 30rpx;
}
.btn-text {
  width: 100%;
  padding: 24rpx;
  background: transparent;
  color: #999;
  border: none;
  font-size: 28rpx;
  margin-top: 16rpx;
}
.bind-hint { color: #666; font-size: 28rpx; margin-bottom: 30rpx; line-height: 1.5; }
.error-msg { color: #e74c3c; font-size: 28rpx; margin-top: 20rpx; }
</style>
