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
      </view>

      <!-- Settings -->
      <view class="section">
        <view class="section-title">推送设置</view>

        <view class="setting-item">
          <text>推送频率</text>
          <picker :value="freqIndex" :range="freqOptions" @change="onFreqChange">
            <text class="setting-value">{{ freqOptions[freqIndex] }}</text>
          </picker>
        </view>

        <view class="setting-item">
          <text>微信订阅消息</text>
          <switch :checked="templateSubscribed" @change="onTemplateChange" />
        </view>
      </view>

      <!-- Notification history link -->
      <view class="nav-item" @click="goNotifications">
        <text>通知历史</text>
        <text class="nav-arrow">›</text>
      </view>

      <!-- Logout -->
      <button class="btn-logout" @click="handleLogout">退出登录</button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { getTemplateSetting, updateTemplateSetting, getTemplateIds } from '@/api/wechat'

const auth = useAuthStore()
const templateSubscribed = ref(false)
const freqOptions = ['每日汇总', '实时推送']
const freqIndex = ref(0)

const accountEmailLabel = computed(() => {
  if (!auth.user) return ''
  if (auth.hasEmail) return auth.user.email
  return '未绑定邮箱（微信登录）'
})

async function hydrateProfile() {
  if (!auth.isLoggedIn) return
  try {
    await auth.refreshMe()
  } catch {
    // ignore
  }
  // default daily (index 0); realtime is index 1
  freqIndex.value = auth.user?.push_frequency === 'realtime' ? 1 : 0
  loadTemplateSetting()
}

onMounted(() => { hydrateProfile() })
onShow(() => { hydrateProfile() })

async function loadTemplateSetting() {
  try {
    const res = await getTemplateSetting()
    templateSubscribed.value = res.subscribed
  } catch (_) { /* ignore */ }
}

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

function goNotifications() {
  uni.navigateTo({ url: '/pages/notifications/index' })
}

async function onFreqChange(e: any) {
  const val = e.detail.value as number
  freqIndex.value = val
  const freq = val === 0 ? 'daily' : 'realtime'
  try {
    const { updatePushFrequency } = await import('@/api/subscriptions')
    await updatePushFrequency(freq)
    if (auth.user) auth.user.push_frequency = freq
    uni.showToast({ title: '更新成功', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err.message || '更新失败', icon: 'none' })
  }
}

async function onTemplateChange(e: any) {
  const val = e.detail.value as boolean
  if (val) {
    try {
      const { template_ids } = await getTemplateIds()
      const nonEmpty = template_ids.filter(Boolean)
      if (nonEmpty.length === 0) {
        uni.showToast({ title: '未配置模板消息', icon: 'none' })
        return
      }
      const { errMsg } = await uni.requestSubscribeMessage({
        tmplIds: nonEmpty,
      })
      if (errMsg !== 'requestSubscribeMessage:ok') {
        uni.showToast({ title: '授权失败', icon: 'none' })
        return
      }
    } catch (_) {
      uni.showToast({ title: '授权失败', icon: 'none' })
      return
    }
  }
  try {
    await updateTemplateSetting(val)
    templateSubscribed.value = val
    uni.showToast({ title: val ? '已开启' : '已关闭', icon: 'success' })
  } catch (err: any) {
    uni.showToast({ title: err.message || '操作失败', icon: 'none' })
  }
}

function handleLogout() {
  uni.showModal({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态',
    confirmText: '退出',
    cancelText: '取消',
    success: (res) => {
      if (!res.confirm) return
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
.user-meta { font-size: 24rpx; color: #3cc51f; margin-top: 8rpx; display: block; }
.section { background: #fff; margin-bottom: 16rpx; padding: 0 30rpx; }
.section-title { font-size: 28rpx; color: #999; padding: 20rpx 0; border-bottom: 1rpx solid #f0f0f0; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 0; border-bottom: 1rpx solid #f8f8f8; font-size: 28rpx; }
.setting-value { color: #999; }
.nav-item { display: flex; justify-content: space-between; background: #fff; padding: 28rpx 30rpx; font-size: 28rpx; margin-bottom: 16rpx; }
.nav-arrow { color: #ccc; font-size: 36rpx; }
.btn-logout { width: 90%; margin: 60rpx auto 0; padding: 24rpx; background: #fff; color: #e74c3c; border: 2rpx solid #e74c3c; border-radius: 12rpx; font-size: 30rpx; display: block; text-align: center; }
</style>
