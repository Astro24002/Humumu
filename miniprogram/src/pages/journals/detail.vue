<template>
  <view class="container">
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="loadError" class="empty">
      <text>{{ loadError }}</text>
      <button size="mini" class="btn-more" @click="goBack">返回</button>
    </view>
    <template v-else-if="journal">
      <view class="header">
        <text class="name">{{ journal.name }}</text>
        <text class="tag">{{ journal.source_type }}</text>
        <text v-if="journal.content_type === 'preprint'" class="tag preprint">预印本</text>
        <text
          v-if="journal.directory_status && journal.directory_status !== 'public'"
          :class="['tag', 'dir', dirClass(journal.directory_status)]"
        >{{ dirStatusLabel(journal.directory_status) }}</text>
        <text v-if="journal.health_status === 'paused'" class="tag paused">抓取暂停</text>
      </view>
      <text v-if="journal.description" class="desc">{{ journal.description }}</text>
      <view v-if="journal.homepage_url || journal.source_url" class="home-row" @click="openHome">
        <text class="home-label">{{ journal.homepage_url ? '主页' : '源' }}</text>
        <text class="home-link">{{ shortUrl(journal.homepage_url || journal.source_url) }}</text>
      </view>

      <view class="subscribe-bar">
        <template v-if="auth.isLoggedIn">
          <button v-if="isSubscribed" class="btn-unsub" @click="unsubscribe">取消订阅</button>
          <button v-else class="btn-sub" @click="subscribe">订阅</button>
        </template>
        <button v-else class="btn-sub" @click="goLogin">登录后订阅</button>
      </view>

      <view class="section-title"><text>最新论文</text></view>
      <view v-if="articlesLoading && !articles.length" class="loading"><text>加载论文...</text></view>
      <template v-else>
        <ArticleCard v-for="a in articles" :key="a.id" :article="a" />
        <view v-if="articles.length === 0" class="empty"><text>{{ journal.health_status === 'paused' ? '暂无论文（抓取已暂停）' : '暂无论文' }}</text></view>
        <view v-if="hasMore" class="more-wrap">
          <button class="btn-more" size="mini" :loading="loadingMore" @click="loadMore">加载更多</button>
        </view>
      </template>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { subscribeJournal, unsubscribeJournal, getSubscribedJournals } from '@/api/subscriptions'
import ArticleCard from '@/components/ArticleCard.vue'

const auth = useAuthStore()
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const articlesLoading = ref(false)
const loadError = ref('')
const isSubscribed = ref(false)
const journalId = ref('')
const offset = ref(0)
const limit = 20
const hasMore = ref(false)

function goBack() {
  uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/journals/index' }) })
}

function dirStatusLabel(s?: string): string {
  const map: Record<string, string> = {
    private: '私有',
    pending_review: '待审公开',
    rejected: '公开未通过',
    hidden: '已下架',
  }
  return map[s || ''] || s || ''
}

function dirClass(s?: string): string {
  if (s === 'pending_review') return 'warn'
  if (s === 'rejected' || s === 'hidden') return 'err'
  return 'info'
}

async function loadArticles(reset: boolean) {
  if (!journalId.value) return
  if (reset) {
    offset.value = 0
    articles.value = []
    articlesLoading.value = true
  } else {
    loadingMore.value = true
  }
  try {
    const ar = await getArticles({
      journal_id: journalId.value,
      limit,
      offset: offset.value,
    })
    articles.value.push(...ar.articles)
    offset.value += ar.articles.length
    const total = ar.total ?? offset.value
    hasMore.value = offset.value < total && ar.articles.length >= limit
  } catch (e: any) {
    if (reset && !articles.value.length) {
      uni.showToast({ title: e?.message || '加载论文失败', icon: 'none' })
    }
  } finally {
    loadingMore.value = false
    articlesLoading.value = false
  }
}

function loadMore() {
  if (!hasMore.value || loadingMore.value) return
  loadArticles(false)
}

onMounted(async () => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  const id = page.$page?.options?.id || page.options?.id
  if (!id) {
    loadError.value = '缺少期刊 ID'
    loading.value = false
    return
  }
  journalId.value = id

  try {
    const [jr, , subRes] = await Promise.all([
      getJournal(id),
      loadArticles(true),
      auth.isLoggedIn ? getSubscribedJournals() : Promise.resolve(null),
    ])
    journal.value = jr
    if (jr?.name) {
      uni.setNavigationBarTitle({ title: jr.name.length > 16 ? `${jr.name.slice(0, 16)}…` : jr.name })
    }
    if (subRes) {
      isSubscribed.value = subRes.journals.some(j => j.id === id)
    }
  } catch (e: any) {
    loadError.value = e?.message || '期刊不存在或无权查看'
  } finally {
    loading.value = false
  }
})

function goLogin() {
  uni.navigateTo({ url: '/pages/login/index' })
}

async function subscribe() {
  if (!auth.isLoggedIn) {
    goLogin()
    return
  }
  try {
    await subscribeJournal(journal.value!.id)
    isSubscribed.value = true
    uni.showToast({ title: '订阅成功', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '订阅失败', icon: 'none' })
  }
}

function shortUrl(url?: string | null): string {
  if (!url) return ''
  try {
    const u = new URL(url)
    const path = u.pathname === '/' ? '' : u.pathname
    const full = `${u.host}${path}`
    return full.length > 40 ? `${full.slice(0, 40)}…` : full
  } catch {
    return url.length > 40 ? `${url.slice(0, 40)}…` : url
  }
}

function openHome() {
  const url = journal.value?.homepage_url || journal.value?.source_url
  if (!url) return
  // #ifdef H5
  window.open(url, '_blank')
  // #endif
  // #ifndef H5
  uni.setClipboardData({ data: url })
  uni.showToast({ title: '链接已复制', icon: 'none' })
  // #endif
}

async function unsubscribe() {
  try {
    await unsubscribeJournal(journal.value!.id)
    isSubscribed.value = false
    uni.showToast({ title: '已取消订阅', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
</script>

<style scoped>
.container { padding-bottom: 30rpx; }
.header { padding: 30rpx; display: flex; align-items: center; gap: 16rpx; }
.name { font-size: 36rpx; font-weight: 600; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag.preprint { color: #2080f0; background: #e8f3ff; }
.tag.dir.info { color: #2080f0; background: #e8f3ff; }
.tag.dir.warn { color: #f0a020; background: #fff7e8; }
.tag.dir.err { color: #d03050; background: #fdecef; }
.tag.paused { color: #d03050; background: #fdecef; }
.home-row { padding: 0 30rpx 16rpx; display: flex; gap: 12rpx; align-items: flex-start; }
.home-label { font-size: 24rpx; color: #999; flex-shrink: 0; }
.home-link { font-size: 24rpx; color: #2080f0; word-break: break-all; }
.desc { padding: 0 30rpx; font-size: 28rpx; color: #666; line-height: 1.6; display: block; }
.subscribe-bar { padding: 20rpx 30rpx; }
.btn-sub, .btn-unsub {
  width: 100%; padding: 20rpx; border-radius: 12rpx; font-size: 30rpx; border: none;
}
.btn-sub { background: #3cc51f; color: #fff; }
.btn-unsub { background: #fff; color: #e74c3c; border: 2rpx solid #e74c3c; }
.section-title { padding: 20rpx 30rpx 10rpx; font-size: 30rpx; font-weight: 500; }
.loading, .empty { text-align: center; padding: 60rpx; color: #999; }
.more-wrap { padding: 24rpx 30rpx 40rpx; text-align: center; }
.btn-more { background: #f5f5f5; color: #666; border: none; }
</style>
