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
        <text v-else-if="auth.hasEmail" class="user-meta muted">微信未关联</text>
        <view v-if="!auth.hasEmail" class="bind-email-hint">
          <text class="bind-email-text">邮件推送需绑定真实邮箱。推荐先在网页用邮箱注册，再用本页合并绑定。</text>
          <text class="bind-email-link" :class="{ busy: profileBusy }" @click="goBindEmail">去绑定</text>
        </view>
        <view v-else-if="!auth.user?.wechat_openid" class="bind-email-hint">
          <text class="bind-email-text">用当前邮箱重新登录即可绑定微信，用于订阅消息</text>
          <text class="bind-email-link" :class="{ busy: profileBusy }" @click="goBindWechat">去绑定微信</text>
        </view>
      </view>

      <!-- Settings -->
      <view class="section">
        <view class="section-title">推送设置</view>

        <view class="setting-item">
          <text>推送频率</text>
          <picker :value="freqIndex" :range="freqOptions" :disabled="profileBusy" @change="onFreqChange">
            <text class="setting-value">{{ freqOptions[freqIndex] }}</text>
          </picker>
        </view>

        <view class="setting-item">
          <text>微信订阅消息</text>
          <switch :checked="templateSubscribed" :disabled="profileBusy" @change="onTemplateChange" />
        </view>
      </view>

      <!-- My journal requests -->
      <view class="section">
        <view class="section-title">我的期刊申请</view>
        <view v-if="requestsLoading && !myRequests.length" class="req-empty"><text>加载中...</text></view>
        <view v-else-if="!myRequests.length" class="req-empty">
          <text>暂无申请记录</text>
          <text class="req-cta" :class="{ busy: profileBusy }" @click="goSubscriptions">去添加 RSS</text>
        </view>
        <view v-else class="req-list" :class="{ busy: requestsLoading || profileBusy }">
          <view v-for="r in myRequests" :key="r.id" class="req-item">
            <text class="req-name">{{ r.journal_name }}</text>
            <view class="req-meta">
              <text class="req-status">{{ requestStatusLabel(r.status) }}</text>
              <text class="req-time">{{ formatDateTime(r.created_at) }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Notification history link -->
      <view class="nav-item" :class="{ busy: profileBusy }" @click="goNotifications">
        <text>通知历史</text>
        <text class="nav-arrow">›</text>
      </view>

      <!-- Logout -->
      <button
        class="btn-logout"
        :disabled="profileBusy"
        :class="{ disabled: profileBusy }"
        @click="handleLogout"
      >退出登录</button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh, onUnload } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { freqLabel, isWechatPlaceholderEmail, requestStatusLabel, formatDateTime } from '@/utils/format'
import { getTemplateSetting, updateTemplateSetting, getTemplateIds } from '@/api/wechat'
import { getMyJournalRequests, type JournalRequest } from '@/api/journals'

const auth = useAuthStore()
const templateSubscribed = ref(false)
const freqOptions = [`${freqLabel('daily')}汇总`, `${freqLabel('realtime')}推送`]
const freqIndex = ref(0)
const freqBusy = ref(false)
const templateBusy = ref(false)
const myRequests = ref<JournalRequest[]>([])
const requestsLoading = ref(false)
/** Drop stale profile hydrations when onShow/pull races mid-flight. */
let profileLoadSeq = 0
let requestsLoadSeq = 0

const profileBusy = computed(() => freqBusy.value || templateBusy.value || requestsLoading.value)

const accountEmailLabel = computed(() => {
  if (!auth.user) return ''
  if (auth.hasEmail && auth.user.email && !isWechatPlaceholderEmail(auth.user.email)) {
    return auth.user.email
  }
  return '未绑定邮箱（微信登录）'
})

async function loadMyRequests() {
  if (!auth.isLoggedIn) {
    myRequests.value = []
    return
  }
  const seq = ++requestsLoadSeq
  requestsLoading.value = true
  try {
    const res = await getMyJournalRequests()
    if (seq !== requestsLoadSeq) return
    myRequests.value = res.requests || []
  } catch {
    if (seq !== requestsLoadSeq) return
  } finally {
    if (seq === requestsLoadSeq) requestsLoading.value = false
  }
}

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
  // Seed from /auth/me payload, then confirm via template-setting endpoint.
  if (typeof auth.user?.wechat_template_subscribed === 'boolean') {
    templateSubscribed.value = auth.user.wechat_template_subscribed
  }
  loadTemplateSetting()
  void loadMyRequests()
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
  if (profileBusy.value) return
  uni.navigateTo({ url: '/pages/notifications/index' })
}

function goSubscriptions() {
  if (profileBusy.value) return
  uni.switchTab({ url: '/pages/subscriptions/index' })
}

function persistUser() {
  if (auth.user) uni.setStorageSync('user', JSON.stringify(auth.user))
}

async function onFreqChange(e: any) {
  if (profileBusy.value) return
  const prev = freqIndex.value
  const val = Number(e.detail.value)
  freqIndex.value = val
  const freq = val === 0 ? 'daily' : 'realtime'
  freqBusy.value = true
  try {
    const { updatePushFrequency } = await import('@/api/subscriptions')
    await updatePushFrequency(freq)
    if (auth.user) {
      auth.user.push_frequency = freq
      persistUser()
    }
    uni.showToast({ title: '更新成功', icon: 'success' })
  } catch (err: any) {
    freqIndex.value = prev
    uni.showToast({ title: err.message || '更新失败', icon: 'none' })
  } finally {
    freqBusy.value = false
  }
}

async function onTemplateChange(e: any) {
  if (profileBusy.value) return
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
    const res = await updateTemplateSetting(val)
    templateSubscribed.value = res.subscribed
    if (auth.user) {
      auth.user.wechat_template_subscribed = res.subscribed
      persistUser()
    }
    uni.showToast({ title: res.subscribed ? '已开启' : '已关闭', icon: 'success' })
  } catch (err: any) {
    templateSubscribed.value = prev
    uni.showToast({ title: err.message || '操作失败', icon: 'none' })
  } finally {
    templateBusy.value = false
  }
}

function goBindEmail() {
  if (profileBusy.value) return
  uni.navigateTo({ url: '/pages/login/index?mode=bind' })
}

function goBindWechat() {
  if (profileBusy.value) return
  uni.navigateTo({ url: '/pages/login/index?mode=bind-wechat' })
}

function handleLogout() {
  if (profileBusy.value) return
  uni.showModal({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态',
    confirmText: '退出',
    cancelText: '取消',
    success: (res) => {
      if (!res.confirm) return
      if (profileBusy.value) return
      auth.logout()
      uni.showToast({ title: '已退出', icon: 'none' })
    },
  })
}
onUnload(() => { profileLoadSeq++; requestsLoadSeq++ })
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
.user-meta.muted { color: #999; }
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
.req-empty { padding: 24rpx 0 32rpx; color: #999; font-size: 26rpx; display: flex; flex-direction: column; gap: 12rpx; }
.req-cta { color: #3cc51f; font-size: 26rpx; }
.req-cta.busy { opacity: 0.45; pointer-events: none; }
.req-list { padding-bottom: 16rpx; }
.req-list.busy { opacity: 0.55; pointer-events: none; }
.req-item { padding: 20rpx 0; border-bottom: 1rpx solid #f5f5f5; }
.req-name { font-size: 28rpx; color: #333; display: block; }
.req-meta { display: flex; gap: 16rpx; margin-top: 8rpx; align-items: center; }
.req-status { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 2rpx 12rpx; border-radius: 8rpx; }
.req-time { font-size: 22rpx; color: #bbb; }
</style>
