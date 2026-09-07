<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可管理个人设置</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <!-- User info -->
      <view class="user-card">
        <text class="user-name">{{ auth.user?.name || '用户' }}</text>
        <text class="user-email">{{ accountEmailLabel }}</text>
        <text v-if="auth.user?.wechat_openid" class="user-meta">微信已关联</text>
        <view v-if="!auth.hasEmail" class="bind-email-hint">
          <text class="bind-email-text">邮件推送需绑定真实邮箱</text>
          <text class="bind-email-link" :class="{ busy: freqBusy || templateBusy }" @click="goBindEmail">去绑定</text>
        </view>
      </view>

      <!-- Settings -->
      <view class="section">
        <view class="section-title">推送设置</view>

        <view class="setting-item">
          <text>推送频率</text>
          <picker :value="freqIndex" :range="freqOptions" :disabled="freqBusy || templateBusy" @change="onFreqChange">
            <text class="setting-value">{{ freqOptions[freqIndex] }}</text>
          </picker>
        </view>

        <view class="setting-item">
          <text>微信订阅消息</text>
          <switch :checked="templateSubscribed" :disabled="templateBusy || freqBusy" @change="onTemplateChange" />
        </view>
      </view>

      <!-- Notification history link -->
      <view class="nav-item" :class="{ busy: freqBusy || templateBusy }" @click="goNotifications">
        <text>通知历史</text>
        <text class="nav-arrow">›</text>
      </view>

      <!-- Logout -->
      <button
        class="btn-logout"
        :disabled="freqBusy || templateBusy"
        :class="{ disabled: freqBusy || templateBusy }"
        @click="handleLogout"
      >退出登录</button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { freqLabel, isWechatPlaceholderEmail } from '@/utils/format'
import { getTemplateSetting, updateTemplateSetting, getTemplateIds } from '@/api/wechat'

const auth = useAuthStore()
const templateSubscribed = ref(false)
const freqOptions = [`${freqLabel('daily')}汇总`, `${freqLabel('realtime')}推送`]
const freqIndex = ref(0)
const freqBusy = ref(false)
const templateBusy = ref(false)
/** Drop stale profile hydrations when onShow/pull races mid-flight. */
let profileLoadSeq = 0

const accountEmailLabel = computed(() => {
  if (!auth.user) return ''
  if (auth.hasEmail && auth.user.email && !isWechatPlaceholderEmail(auth.user.email)) {
    return auth.user.email
  }
  return '未绑定邮箱（微信登录）'
})

async function hydrateProfile() {
  if (!auth.isLoggedIn) return
  const seq = ++profileLoadSeq
  try {
    await auth.refreshMe()
  } catch {
    // ignore
  }
  if (seq !== profileLoadSeq) return
  // default daily (index 0); realtime is index 1
  freqIndex.value = auth.user?.push_frequency === 'realtime' ? 1 : 0
  loadTemplateSetting()
}

onShow(() => { hydrateProfile() })

onPullDownRefresh(async () => {
  try {
    await hydrateProfile()
  } finally {
    uni.stopPullDownRefresh()
  }
})

async function loadTemplateSetting() {
  try {
    const res = await getTemplateSetting()
    templateSubscribed.value = res.subscribed
  } catch (_) { /* ignore */ }
}


function goNotifications() {
  if (freqBusy.value || templateBusy.value) return
  uni.navigateTo({ url: '/pages/notifications/index' })
}

async function onFreqChange(e: any) {
  if (freqBusy.value || templateBusy.value) return
  const prev = freqIndex.value
  const val = Number(e.detail.value)
  freqIndex.value = val
  const freq = val === 0 ? 'daily' : 'realtime'
  freqBusy.value = true
  try {
    const { updatePushFrequency } = await import('@/api/subscriptions')
    await updatePushFrequency(freq)
    if (auth.user) auth.user.push_frequency = freq
    uni.showToast({ title: '更新成功', icon: 'success' })
  } catch (err: any) {
    freqIndex.value = prev
    uni.showToast({ title: err.message || '更新失败', icon: 'none' })
  } finally {
    freqBusy.value = false
  }
}

async function onTemplateChange(e: any) {
  if (templateBusy.value || freqBusy.value) return
  const val = e.detail.value as boolean
  const prev = templateSubscribed.value
  templateBusy.value = true
  try {
    if (val) {
      try {
        const { template_ids } = await getTemplateIds()
        const nonEmpty = template_ids.filter(Boolean)
        if (nonEmpty.length === 0) {
          uni.showToast({ title: '未配置模板消息', icon: 'none' })
          templateSubscribed.value = prev
          return
        }
        const { errMsg } = await uni.requestSubscribeMessage({
          tmplIds: nonEmpty,
        })
        if (errMsg !== 'requestSubscribeMessage:ok') {
          uni.showToast({ title: '授权失败', icon: 'none' })
          templateSubscribed.value = prev
          return
        }
      } catch (_) {
        uni.showToast({ title: '授权失败', icon: 'none' })
        templateSubscribed.value = prev
        return
      }
    }
    await updateTemplateSetting(val)
    templateSubscribed.value = val
    uni.showToast({ title: val ? '已开启' : '已关闭', icon: 'success' })
  } catch (err: any) {
    templateSubscribed.value = prev
    uni.showToast({ title: err.message || '操作失败', icon: 'none' })
  } finally {
    templateBusy.value = false
  }
}

function goBindEmail() {
  if (freqBusy.value || templateBusy.value) return
  uni.navigateTo({ url: '/pages/login/index?mode=bind' })
}

function handleLogout() {
  if (freqBusy.value || templateBusy.value) return
  uni.showModal({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态',
    confirmText: '退出',
    cancelText: '取消',
    success: (res) => {
      if (!res.confirm) return
      if (freqBusy.value || templateBusy.value) return
      auth.logout()
      uni.showToast({ title: '已退出', icon: 'none' })
    },
  })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.user-card { background: #fff; padding: 40rpx 30rpx; margin-bottom: 16rpx; }
.user-name { font-size: 36rpx; font-weight: 600; display: block; }
.user-email { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
.bind-email-hint { margin-top: 16rpx; display: flex; align-items: center; gap: 16rpx; flex-wrap: wrap; }
.bind-email-text { font-size: 24rpx; color: #888; }
.bind-email-link { font-size: 24rpx; color: #3cc51f; }
.user-meta { font-size: 24rpx; color: #3cc51f; margin-top: 8rpx; display: block; }
.section { background: #fff; margin-bottom: 16rpx; padding: 0 30rpx; }
.section-title { font-size: 28rpx; color: #999; padding: 20rpx 0; border-bottom: 1rpx solid #f0f0f0; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 0; border-bottom: 1rpx solid #f8f8f8; font-size: 28rpx; }
.setting-value { color: #999; }
.nav-item { display: flex; justify-content: space-between; background: #fff; padding: 28rpx 30rpx; font-size: 28rpx; margin-bottom: 16rpx; }
.nav-arrow { color: #ccc; font-size: 36rpx; }
.btn-logout { width: 90%; margin: 60rpx auto 0; padding: 24rpx; background: #fff; color: #e74c3c; border: 2rpx solid #e74c3c; border-radius: 12rpx; font-size: 30rpx; display: block; text-align: center; }
.btn-logout.disabled { opacity: 0.45; }
.nav-item.busy { opacity: 0.45; pointer-events: none; }
.bind-email-link.busy { opacity: 0.45; pointer-events: none; }
</style>
