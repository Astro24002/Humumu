<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可查看通知</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <view class="title-row">
        <text class="page-title">通知历史</text>
        <text v-if="!loading && total != null" class="count-badge">{{ total }} 条</text>
      </view>
      <view class="filters" :class="{ 'filters-busy': loading }">
        <text :class="['chip', channelFilter === '' && 'on']" @click="setChannel('')">全部渠道</text>
        <text :class="['chip', channelFilter === 'email' && 'on']" @click="setChannel('email')">{{ channelLabel('email') }}</text>
        <text :class="['chip', channelFilter === 'wechat' && 'on']" @click="setChannel('wechat')">{{ channelLabel('wechat') }}</text>
      </view>
      <view class="filters" :class="{ 'filters-busy': loading }">
        <text :class="['chip', statusFilter === '' && 'on']" @click="setStatus('')">全部状态</text>
        <text :class="['chip', statusFilter === 'sent' && 'on']" @click="setStatus('sent')">{{ notifStatusLabel('sent') }}</text>
        <text :class="['chip', statusFilter === 'failed' && 'on']" @click="setStatus('failed')">{{ notifStatusLabel('failed') }}</text>
        <text :class="['chip', statusFilter === 'pending' && 'on']" @click="setStatus('pending')">{{ notifStatusLabel('pending') }}</text>
      </view>
      <view v-if="loading && !notifications.length" class="loading"><text>加载中...</text></view>
      <view v-else-if="!notifications.length" class="empty">
        <text>{{ emptyHint }}</text>
        <button v-if="hasActiveFilters" size="mini" class="btn-empty" :disabled="loading" @click="clearFilters">清除筛选</button>
        <button v-else size="mini" class="btn-empty" :disabled="loading" @click="goSubscriptions">管理订阅</button>
      </view>
      <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
        <view v-for="n in notifications" :key="n.id" class="notif-item" :class="{ busy: loading }" @click="goArticle(n.article_id)">
          <text v-if="n.article_title" class="title">{{ n.article_title }}</text>
          <view class="notif-header">
            <text :class="['tag', n.channel === 'wechat' ? 'tag-wechat' : 'tag-email']">
              {{ channelLabel(n.channel) }}
            </text>
            <text :class="['status', n.status]">{{ notifStatusLabel(n.status) }}</text>
            <text v-for="r in (n.match_reasons || [])" :key="r" class="reason">{{ reasonLabel(r) }}</text>
          </view>
          <text v-if="n.error_message" class="error">{{ n.error_message }}</text>
          <text class="time">{{ formatDateTime(n.created_at) }}</text>
        </view>
        <view v-if="loadingMore" class="loading-more"><text>加载中...</text></view>
        <view v-else-if="hasMore" class="loading-more"><text>上拉加载更多</text></view>
        <view v-else-if="notifications.length" class="loading-more"><text>已显示全部</text></view>
      </scroll-view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh, onUnload } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { getNotifications, type Notification } from '@/api/notifications'
import { formatDateTime, reasonLabel, notifStatusLabel, channelLabel } from '@/utils/format'

const auth = useAuthStore()
const notifications = ref<Notification[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20
const total = ref<number | null>(null)
const statusFilter = ref('')
const channelFilter = ref('')
/** Drop stale notification list responses when filters race mid-flight. */
let notifLoadSeq = 0

const hasActiveFilters = computed(() => Boolean(statusFilter.value || channelFilter.value))

const emptyHint = computed(() => {
  if (hasActiveFilters.value) return '当前筛选下暂无通知'
  return '暂无通知'
})

function goSubscriptions() {
  if (loading.value) return
  uni.switchTab({ url: '/pages/subscriptions/index' })
}


onShow(() => {
  if (auth.isLoggedIn) fetchNotifications(true)
  else {
    notifications.value = []
    total.value = null
    hasMore.value = false
    loading.value = false
  }
})

onPullDownRefresh(async () => {
  try {
    if (auth.isLoggedIn) await fetchNotifications(true)
  } finally {
    uni.stopPullDownRefresh()
  }
})


function setStatus(s: string) {
  if (loading.value || statusFilter.value === s) return
  statusFilter.value = s
  fetchNotifications(true)
}

function setChannel(c: string) {
  if (loading.value || channelFilter.value === c) return
  channelFilter.value = c
  fetchNotifications(true)
}

function clearFilters() {
  if (loading.value) return
  statusFilter.value = ''
  channelFilter.value = ''
  fetchNotifications(true)
}

async function fetchNotifications(reset = false) {
  if (reset) {
    offset.value = 0
    notifications.value = []
    hasMore.value = true
    total.value = null
    loadingMore.value = false
    loading.value = true
  } else {
    if (!hasMore.value || loadingMore.value || loading.value) return
    loadingMore.value = true
  }
  const seq = ++notifLoadSeq
  try {
    const res = await getNotifications({
      limit,
      offset: offset.value,
      status: statusFilter.value || undefined,
      channel: channelFilter.value || undefined,
    })
    if (seq !== notifLoadSeq) return
    notifications.value.push(...res.notifications)
    offset.value += res.notifications.length
    if (typeof res.total === 'number') total.value = res.total
    hasMore.value = total.value != null
      ? notifications.value.length < total.value
      : res.notifications.length === limit
  } catch (e: any) {
    if (seq !== notifLoadSeq) return
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    if (seq === notifLoadSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function loadMore() { fetchNotifications(false) }



function goArticle(articleId: string) {
  if (loading.value || !articleId) return
  uni.navigateTo({ url: `/pages/article/detail?id=${articleId}` })
}
onUnload(() => { notifLoadSeq++ })
</script>

<style scoped>
.container { min-height: 100vh; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.title-row { display: flex; align-items: center; gap: 16rpx; padding: 24rpx 30rpx 8rpx; background: #f8f8f8; }
.page-title { font-size: 32rpx; font-weight: 600; color: #333; }
.count-badge { font-size: 22rpx; color: #888; background: #eee; padding: 4rpx 12rpx; border-radius: 12rpx; }
.filters { display: flex; flex-wrap: wrap; gap: 16rpx; padding: 16rpx 30rpx; background: #f8f8f8; }
.filters-busy { opacity: 0.55; pointer-events: none; }
.chip {
  font-size: 24rpx; padding: 8rpx 20rpx; border-radius: 24rpx;
  background: #fff; color: #666; border: 1rpx solid #eee;
}
.chip.on { background: #e8f8e0; color: #3cc51f; border-color: #3cc51f; }
.loading, .empty { text-align: center; padding: 80rpx 40rpx; color: #999; }
.btn-empty { margin-top: 24rpx; background: #e8f8e0; color: #3cc51f; border: none; }
.scroll-view { height: calc(100vh - 200rpx); }
.notif-item.busy { opacity: 0.55; pointer-events: none; }
.notif-item { padding: 24rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.title { font-size: 28rpx; color: #333; font-weight: 500; line-height: 1.4; display: block; margin-bottom: 10rpx; }
.notif-header { display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.tag { font-size: 22rpx; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag-wechat { background: #e8f8e0; color: #3cc51f; }
.tag-email { background: #e8f0fe; color: #1a73e8; }
.status { font-size: 24rpx; color: #999; }
.status.sent { color: #3cc51f; }
.status.failed { color: #e74c3c; }
.reason { font-size: 22rpx; padding: 2rpx 10rpx; border-radius: 8rpx; background: #fff7e6; color: #d48806; }
.error { font-size: 24rpx; color: #e74c3c; margin-top: 8rpx; display: block; }
.time { font-size: 24rpx; color: #ccc; margin-top: 8rpx; display: block; }
.loading-more { text-align: center; padding: 20rpx; color: #999; }
button:disabled { opacity: 0.55; }
</style>
