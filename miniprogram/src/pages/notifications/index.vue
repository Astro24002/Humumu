<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可查看通知</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <view v-if="loading" class="loading"><text>加载中...</text></view>
      <view v-else-if="notifications.length === 0" class="empty"><text>暂无通知</text></view>
      <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
        <view v-for="n in notifications" :key="n.id" class="notif-item" @click="goArticle(n.article_id)">
          <view class="notif-header">
            <text :class="['tag', n.channel === 'wechat' ? 'tag-wechat' : 'tag-email']">
              {{ n.channel === 'wechat' ? '微信' : '邮件' }}
            </text>
            <text :class="['status', n.status]">{{ statusText(n.status) }}</text>
          </view>
          <text class="time">{{ formatDate(n.created_at) }}</text>
        </view>
        <view class="loading-more" v-if="hasMore"><text>加载更多...</text></view>
      </scroll-view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getNotifications, type Notification } from '@/api/notifications'
import { formatDate } from '@/utils/format'

const auth = useAuthStore()
const notifications = ref<Notification[]>([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20

onMounted(() => {
  if (auth.isLoggedIn) fetchNotifications()
  else loading.value = false
})

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

async function fetchNotifications() {
  if (!hasMore.value) return
  loading.value = true
  try {
    const res = await getNotifications({ limit, offset: offset.value })
    notifications.value.push(...res.notifications)
    offset.value += limit
    hasMore.value = res.notifications.length === limit
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function loadMore() { fetchNotifications() }

function statusText(s: string) {
  switch (s) {
    case 'sent': return '已发送'
    case 'pending': return '待发送'
    case 'failed': return '发送失败'
    default: return s
  }
}

function goArticle(articleId: string) {
  uni.navigateTo({ url: `/pages/article/detail?id=${articleId}` })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.loading, .empty { text-align: center; padding: 80rpx; color: #999; }
.scroll-view { height: 100vh; }
.notif-item { padding: 24rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.notif-header { display: flex; align-items: center; gap: 12rpx; }
.tag { font-size: 22rpx; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag-wechat { background: #e8f8e0; color: #3cc51f; }
.tag-email { background: #e8f0fe; color: #1a73e8; }
.status { font-size: 24rpx; color: #999; }
.status.sent { color: #3cc51f; }
.status.failed { color: #e74c3c; }
.time { font-size: 24rpx; color: #ccc; margin-top: 8rpx; display: block; }
.loading-more { text-align: center; padding: 20rpx; color: #999; }
</style>
