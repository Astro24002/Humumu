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
        <text class="tag">{{ sourceTypeLabel(journal.source_type) }}</text>
        <text v-if="journal.content_type === 'preprint'" class="tag preprint">{{ contentTypeLabel(journal.content_type) }}</text>
        <text
          v-if="journal.directory_status && journal.directory_status !== 'public'"
          :class="['tag', 'dir', dirStatusClass(journal.directory_status)]"
        >{{ dirStatusLabel(journal.directory_status) }}</text>
        <text v-if="journal.health_status === 'paused'" class="tag paused">{{ healthStatusLabel(journal.health_status) }}</text>
      </view>
      <text v-if="journal.description" class="desc">{{ journal.description }}</text>
      <view v-if="journal.homepage_url || journal.source_url" class="home-row" @click="openHome">
        <text class="home-label">{{ journal.homepage_url ? '主页' : '源' }}</text>
        <text class="home-link">{{ shortUrl(journal.homepage_url || journal.source_url) }}</text>
      </view>

      <view class="subscribe-bar">
        <template v-if="auth.isLoggedIn">
          <button v-if="isSubscribed" class="btn-unsub" :disabled="subBusy" @click="unsubscribe">取消订阅</button>
          <button v-else class="btn-sub" :disabled="subBusy" @click="subscribe">{{ subBusy ? '处理中...' : '订阅' }}</button>
        </template>
        <button v-else class="btn-sub" @click="goLogin">登录后订阅</button>
      </view>

      <view class="section-title">
        <text>最新论文</text>
        <text v-if="articlesTotal > 0" class="count-badge">{{ articlesTotal }} 篇</text>
      </view>
      <view v-if="articlesLoading && !articles.length" class="loading"><text>加载论文...</text></view>
      <template v-else>
        <ArticleCard v-for="a in articles" :key="a.id" :article="a" />
        <view v-if="articles.length === 0" class="empty">
          <text>{{ journal.health_status === 'paused' ? '暂无论文（抓取已暂停）' : '暂无论文' }}</text>
          <button size="mini" class="btn-more" @click="goPlaza">返回期刊广场</button>
        </view>
        <view v-if="hasMore" class="more-wrap">
          <button class="btn-more" size="mini" :loading="loadingMore" :disabled="loadingMore || articlesLoading" @click="loadMore">
            {{ loadingMore ? '加载中...' : '加载更多' }}
          </button>
        </view>
        <view v-else-if="articles.length && !articlesLoading" class="more-wrap end">
          <text class="end-hint">已显示全部</text>
        </view>
      </template>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { subscribeJournal, unsubscribeJournal, getSubscribedJournals } from '@/api/subscriptions'
import { dirStatusLabel, dirStatusClass, shortUrl, sourceTypeLabel, contentTypeLabel, healthStatusLabel } from '@/utils/format'
import ArticleCard from '@/components/ArticleCard.vue'

const auth = useAuthStore()
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const articlesLoading = ref(false)
const loadError = ref('')
const isSubscribed = ref(false)
const subBusy = ref(false)
const journalId = ref('')
const offset = ref(0)
const limit = 20
const hasMore = ref(false)
const articlesTotal = ref(0)
/** Drop stale article-list responses when reset races loadMore mid-flight. */
let articlesLoadSeq = 0

function goPlaza() {
  uni.switchTab({ url: '/pages/journals/index' })
}

function goBack() {
  uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/journals/index' }) })
}

async function loadArticles(reset: boolean) {
  if (!journalId.value) return
  if (reset) {
    offset.value = 0
    articles.value = []
    articlesTotal.value = 0
    articlesLoading.value = true
  } else {
    if (loadingMore.value || articlesLoading.value) return
    loadingMore.value = true
  }
  const seq = ++articlesLoadSeq
  try {
    const ar = await getArticles({
      journal_id: journalId.value,
      limit,
      offset: offset.value,
    })
    if (seq !== articlesLoadSeq) return
    articles.value.push(...ar.articles)
    offset.value += ar.articles.length
    if (typeof ar.total === 'number') articlesTotal.value = ar.total
    else if (reset) articlesTotal.value = ar.articles.length
    const total = articlesTotal.value || offset.value
    hasMore.value = offset.value < total && ar.articles.length >= limit
  } catch (e: any) {
    if (seq !== articlesLoadSeq) return
    if (reset && !articles.value.length) {
      uni.showToast({ title: e?.message || '加载论文失败', icon: 'none' })
    }
  } finally {
    if (seq === articlesLoadSeq) {
      loadingMore.value = false
      articlesLoading.value = false
    }
  }
}

function loadMore() {
  if (!hasMore.value || loadingMore.value || articlesLoading.value) return
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
    // Prefer journal.article_count until the paged list reports total.
    if (typeof jr?.article_count === 'number' && jr.article_count > 0 && !articlesTotal.value) {
      articlesTotal.value = jr.article_count
    }
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


async function subscribe() {
  if (!auth.isLoggedIn) {
    goLogin()
    return
  }
  if (subBusy.value) return
  subBusy.value = true
  try {
    await subscribeJournal(journal.value!.id)
    isSubscribed.value = true
    uni.showToast({ title: '订阅成功', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '订阅失败', icon: 'none' })
  } finally {
    subBusy.value = false
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

function unsubscribe() {
  if (!journal.value || subBusy.value) return
  const name = journal.value.name
  uni.showModal({
    title: '取消订阅',
    content: `确认取消订阅「${name}」？之后将不再收到该源的更新推送。`,
    confirmText: '取消订阅',
    cancelText: '返回',
    success: async (res) => {
      if (!res.confirm || !journal.value || subBusy.value) return
      subBusy.value = true
      try {
        await unsubscribeJournal(journal.value.id)
        isSubscribed.value = false
        uni.showToast({ title: '已取消订阅', icon: 'success' })
      } catch (e: any) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      } finally {
        subBusy.value = false
      }
    },
  })
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
.section-title {
  padding: 20rpx 30rpx 10rpx; font-size: 30rpx; font-weight: 500;
  display: flex; align-items: center; gap: 12rpx;
}
.count-badge {
  font-size: 22rpx; color: #666; background: #eee; padding: 4rpx 14rpx;
  border-radius: 20rpx; font-weight: 400;
}
.loading, .empty { text-align: center; padding: 60rpx; color: #999; }
.more-wrap { padding: 24rpx 30rpx 40rpx; text-align: center; }
.more-wrap.end { padding-top: 8rpx; }
.end-hint { font-size: 24rpx; color: #bbb; }
.btn-more { background: #f5f5f5; color: #666; border: none; }
button:disabled { opacity: 0.55; }
</style>
