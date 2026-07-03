<template>
  <view class="container">
    <view class="tabs">
      <text :class="['tab', tab === 'all' && 'active']" @click="switchTab('all')">全部</text>
      <text v-if="auth.isLoggedIn" :class="['tab', tab === 'subscribed' && 'active']" @click="switchTab('subscribed')">已订阅</text>
    </view>

    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="articles.length === 0" class="empty"><text>暂无论文</text></view>
    <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
      <ArticleCard v-for="a in articles" :key="a.id" :article="a" />
      <view class="loading-more" v-if="hasMore"><text>加载更多...</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getArticles, getMyFeed, type Article } from '@/api/articles'
import ArticleCard from '@/components/ArticleCard.vue'

const auth = useAuthStore()
const tab = ref<'all' | 'subscribed'>('all')
const articles = ref<Article[]>([])
const loading = ref(true)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20

onMounted(() => {
  if (auth.isLoggedIn) tab.value = 'subscribed'
  fetchArticles()
})

function switchTab(t: 'all' | 'subscribed') {
  tab.value = t
  articles.value = []
  offset.value = 0
  hasMore.value = true
  fetchArticles()
}

async function fetchArticles() {
  if (!hasMore.value) return
  loading.value = true
  try {
    let res
    if (tab.value === 'subscribed' && auth.isLoggedIn) {
      res = await getMyFeed({ limit, offset: offset.value })
    } else {
      res = await getArticles({ limit, offset: offset.value })
    }
    articles.value.push(...res.articles)
    offset.value += limit
    hasMore.value = res.articles.length === limit
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function loadMore() {
  fetchArticles()
}
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; padding: 20rpx 30rpx; gap: 30rpx; background: #f8f8f8; }
.tab { font-size: 30rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx; color: #999; font-size: 28rpx; }
.scroll-view { height: calc(100vh - 100rpx); }
.loading-more { text-align: center; padding: 20rpx; color: #999; font-size: 26rpx; }
</style>
