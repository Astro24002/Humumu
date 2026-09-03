<template>
  <view class="login-container">
    <view class="logo">
      <text class="logo-text">Humumu</text>
      <text class="logo-desc">关注最新学术动态</text>
    </view>

    <!-- Already logged in via wx but has no email -->
    <view v-if="needsBind">
      <view class="bind-hint">绑定已有账号以同步订阅数据</view>
      <uni-forms ref="formRef" :model="form">
        <uni-forms-item label="邮箱" name="email">
          <uni-easyinput v-model="form.email" placeholder="请输入邮箱" type="email" />
        </uni-forms-item>
        <uni-forms-item label="密码" name="password">
          <uni-easyinput v-model="form.password" placeholder="请输入密码" type="password" />
        </uni-forms-item>
      </uni-forms>
      <button class="btn-primary" @click="handleBind">绑定账号</button>
      <button class="btn-text" @click="skipBind">跳过，直接使用</button>
    </view>

    <!-- Initial login screen -->
    <view v-else>
      <button class="btn-primary" @click="handleWeChatLogin" :loading="loading">
        微信一键登录
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

onMounted(() => {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1] as any
  const q = (cur && cur.options) || {}
  returnTo.value = normalizePath(q.from || q.redirect || '')
  if (auth.isLoggedIn) {
    goAfterLogin()
  }
})

async function handleWeChatLogin() {
  loading.value = true
  error.value = ''
  try {
    const { code } = await uni.login()
    wxCode.value = code
    const res = await wechatLogin(code)
    auth.save(res.token, res.user)
    if (!res.has_email) {
      needsBind.value = true
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
  if (!form.value.email || !form.value.password) {
    error.value = '请填写邮箱和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await bindAccount(wxCode.value, form.value.email, form.value.password)
    auth.save(res.token, res.user)
    goAfterLogin()
  } catch (e: any) {
    error.value = e.message || '绑定失败'
  } finally {
    loading.value = false
  }
}

function skipBind() {
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
.bind-hint { color: #666; font-size: 28rpx; margin-bottom: 30rpx; }
.error-msg { color: #e74c3c; font-size: 28rpx; margin-top: 20rpx; }
</style>
