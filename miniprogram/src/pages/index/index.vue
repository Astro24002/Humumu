<template>
  <view class="container">
    <view class="tabs">
      <text :class="['tab', tab === 'all' && 'active']" @click="switchTab('all')">全部</text>
      <text v-if="auth.isLoggedIn" :class="['tab', tab === 'updates' && 'active']" @click="switchTab('updates')">我的更新</text>
      <text v-if="auth.isLoggedIn && tab === 'updates'" :class="['tab', filter === 'unread' && 'active']" @click="setFilter('unread')">未读</text>
      <text v-if="auth.isLoggedIn && tab === 'updates'" :class="['tab', filter === 'starred' && 'active']" @click="setFilter('starred')">星标</text>
    </view>

    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="!items.length" class="empty"><text>暂无论文</text></view>
    <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
      <view
        v-for="a in items"
        :key="a.id"
        class="card"
        @click="goDetail(a.id)"
      >
        <view class="meta">
          <text class="journal">{{ a.journal_name }}</text>
          <text v-if="a.content_type === 'preprint'" class="badge">预印本</text>
          <text v-for="r in a.reasons" :key="r" class="badge reason">{{ reasonLabel(r) }}</text>
        </view>
        <text class="title" :class="{ unread: a.unread }">{{ a.title }}</text>
        <text class="authors" v-if="a.authors?.length">{{ a.authors.slice(0, 3).join(', ') }}</text>
        <text class="date" v-if="a.publish_date">{{ a.publish_date }}</text>
      </view>
      <view class="loading-more" v-if="hasMore"><text>加载更多...</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getArticles } from '@/api/articles'
import { getMyUpdates } from '@/api/myUpdates'

interface FeedItem {
  id: string
  title: string
  authors: string[]
  journal_name: string
  publish_date: string | null
  content_type?: string
  reasons: string[]
  unread?: boolean
}

const auth = useAuthStore()
const tab = ref<'all' | 'updates'>('all')
const filter = ref('')
const items = ref<FeedItem[]>([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20

onMounted(() => {
  if (auth.isLoggedIn) tab.value = 'updates'
  fetchItems()
})

function reasonLabel(r: string): string {
  if (r === 'journal') return '期刊'
  if (r === 'author') return '作者'
  if (r === 'keyword') return '关键词'
  return r
}

function switchTab(t: 'all' | 'updates') {
  tab.value = t
  filter.value = ''
  resetAndFetch()
}

function setFilter(f: string) {
  filter.value = filter.value === f ? '' : f
  resetAndFetch()
}

function resetAndFetch() {
  items.value = []
  offset.value = 0
  hasMore.value = true
  fetchItems()
}

async function fetchItems() {
  if (!hasMore.value && items.value.length) return
  loading.value = true
  try {
    if (tab.value === 'updates' && auth.isLoggedIn) {
      const res = await getMyUpdates({
        limit,
        offset: offset.value,
        filter: filter.value || undefined,
      })
      const mapped: FeedItem[] = res.updates.map(u => ({
        id: u.article_id,
        title: u.title,
        authors: u.authors || [],
        journal_name: u.journal_name,
        publish_date: u.publish_date,
        content_type: u.content_type,
        reasons: u.reasons || [],
        unread: !u.status?.is_read,
      }))
      items.value.push(...mapped)
      offset.value += limit
      hasMore.value = res.updates.length === limit
    } else {
      const res = await getArticles({ limit, offset: offset.value })
      const mapped: FeedItem[] = res.articles.map(a => ({
        id: a.id,
        title: a.title,
        authors: a.authors || [],
        journal_name: a.journal_name,
        publish_date: a.publish_date,
        reasons: [],
      }))
      items.value.push(...mapped)
      offset.value += limit
      hasMore.value = res.articles.length === limit
    }
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function loadMore() {
  fetchItems()
}

function goDetail(id: string) {
  uni.navigateTo({ url: `/pages/article/detail?id=${id}` })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; flex-wrap: wrap; padding: 20rpx 30rpx; gap: 24rpx; background: #f8f8f8; }
.tab { font-size: 28rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx; color: #999; font-size: 28rpx; }
.scroll-view { height: calc(100vh - 100rpx); }
.loading-more { text-align: center; padding: 20rpx; color: #999; font-size: 26rpx; }
.card { background: #fff; padding: 28rpx 30rpx; border-bottom: 1rpx solid #f0f0f0; }
.meta { display: flex; flex-wrap: wrap; gap: 12rpx; margin-bottom: 8rpx; align-items: center; }
.journal { font-size: 24rpx; color: #3cc51f; }
.badge { font-size: 20rpx; background: #eef6ff; color: #3a7bd5; padding: 2rpx 10rpx; border-radius: 6rpx; }
.badge.reason { background: #fff7e6; color: #d48806; }
.title { font-size: 30rpx; color: #333; line-height: 1.4; display: block; }
.title.unread { font-weight: 600; }
.authors { font-size: 24rpx; color: #888; margin-top: 8rpx; display: block; }
.date { font-size: 22rpx; color: #aaa; margin-top: 6rpx; display: block; }
</style>
