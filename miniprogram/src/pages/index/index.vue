<template>
  <view class="container">
    <view class="tabs" :class="{ 'tabs-busy': loading }">
      <text :class="['tab', tab === 'all' && 'active']" @click="switchTab('all')">全部</text>
      <text v-if="auth.isLoggedIn" :class="['tab', tab === 'updates' && 'active']" @click="switchTab('updates')">我的更新</text>
      <text v-if="tab === 'all'" :class="['tab', contentType === 'journal' && 'active']" @click="setContentType('journal')">{{ contentTypeLabel('journal') }}</text>
      <text v-if="tab === 'all'" :class="['tab', contentType === 'preprint' && 'active']" @click="setContentType('preprint')">{{ contentTypeLabel('preprint') }}</text>
      <text v-if="tab === 'all'" :class="['tab', sourceType === 'rss' && 'active']" @click="setSourceType('rss')">{{ sourceTypeLabel('rss') }}</text>
      <text v-if="tab === 'all'" :class="['tab', sourceType === 'arxiv' && 'active']" @click="setSourceType('arxiv')">{{ sourceTypeLabel('arxiv') }}</text>
      <text v-if="tab === 'all'" :class="['tab', sourceType === 'cnki' && 'active']" @click="setSourceType('cnki')">{{ sourceTypeLabel('cnki') }}</text>
      <text v-if="auth.isLoggedIn && tab === 'updates'" :class="['tab', filter === 'unread' && 'active']" @click="setFilter('unread')">未读</text>
      <text v-if="auth.isLoggedIn && tab === 'updates'" :class="['tab', filter === 'starred' && 'active']" @click="setFilter('starred')">星标</text>
      <text v-if="auth.isLoggedIn && tab === 'updates'" :class="['tab', filter === 'later' && 'active']" @click="setFilter('later')">稍后再看</text>
    </view>

    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="!items.length" class="empty">
      <text>{{ emptyHint }}</text>
      <button
        v-if="tab === 'updates' && auth.isLoggedIn && !filter"
        size="mini"
        class="btn-empty"
        :disabled="loading"
        @click="goJournals"
      >去订阅期刊</button>
      <button
        v-if="tab === 'updates' && auth.isLoggedIn && !filter"
        size="mini"
        class="btn-empty ghost"
        :disabled="loading"
        @click="goSubscriptions"
      >管理订阅</button>
      <button
        v-else-if="tab === 'updates' && auth.isLoggedIn && filter"
        size="mini"
        class="btn-empty"
        :disabled="loading"
        @click="clearFilter"
      >查看全部更新</button>
      <button
        v-else-if="tab === 'all' && (contentType || sourceType)"
        size="mini"
        class="btn-empty"
        :disabled="loading"
        @click="clearContentType"
      >清除筛选</button>
      <button
        v-else-if="tab === 'all'"
        size="mini"
        class="btn-empty"
        :disabled="loading"
        @click="goJournals"
      >浏览期刊</button>
    </view>
    <scroll-view v-else scroll-y @scrolltolower="loadMore" class="scroll-view">
      <view
        v-for="a in items"
        :key="a.id"
        class="card"
        :class="{ busy: loading || originalClickBusy.has(a.id) }"
        @click="goDetail(a.id)"
      >
        <view class="meta">
          <text
            v-if="a.journal_id"
            class="journal link"
            :class="{ busy: loading || originalClickBusy.has(a.id) }"
            @click.stop="goJournal(a.journal_id, a.id)"
          >{{ a.journal_name }}</text>
          <text v-else class="journal">{{ a.journal_name }}</text>
          <text v-if="a.content_type === 'preprint'" class="badge">{{ contentTypeLabel(a.content_type) }}</text>
          <text v-if="a.journal_source_type" class="badge source">{{ sourceTypeLabel(a.journal_source_type) }}</text>
          <text v-for="r in (a.reasons || [])" :key="r" class="badge reason">{{ reasonLabel(r) }}</text>
        </view>
        <text class="title" :class="{ unread: a.unread }">{{ a.title }}</text>
        <text class="authors" v-if="a.authors?.length">
          {{ formatAuthors(a.authors) }}
        </text>
        <text class="date" v-if="a.publish_date">{{ formatDate(a.publish_date) }}</text>
        <text class="snippet" v-if="a.abstract">{{ truncateAbstract(a.abstract) }}</text>
        <view v-if="a.doi || a.original_url || a.url" class="actions" @click.stop>
          <text
            v-if="a.doi"
            class="action-link"
            :class="{ disabled: loading || originalClickBusy.has(a.id) }"
            @click="copyLink(doiUrl(a.doi), a)"
          >DOI</text>
          <text
            v-if="a.original_url || a.url"
            class="action-link"
            :class="{ disabled: loading || originalClickBusy.has(a.id) }"
            @click="copyLink(a.original_url || a.url || '', a)"
          >原文</text>
        </view>
      </view>
      <view v-if="loadingMore" class="loading-more"><text>加载中...</text></view>
      <view v-else-if="hasMore" class="loading-more"><text>上拉加载更多</text></view>
      <view v-else-if="items.length" class="loading-more"><text>已显示全部</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow, onPullDownRefresh, onUnload } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { getArticles } from '@/api/articles'
import { getMyUpdates } from '@/api/myUpdates'
import { recordOriginalClick, updateArticleStatus } from '@/api/reading'
import { truncateAbstract } from '@/utils/abstract'
import { formatDate, reasonLabel, formatAuthors, contentTypeLabel, sourceTypeLabel, doiUrl } from '@/utils/format'

interface FeedItem {
  id: string
  title: string
  authors: string[]
  journal_id?: string
  journal_name: string
  publish_date: string | null
  content_type: string
  journal_source_type?: string
  reasons: string[]
  unread?: boolean
  abstract: string
  doi?: string | null
  url: string
  original_url?: string
}

const auth = useAuthStore()
const tab = ref<'all' | 'updates'>('all')
const filter = ref('')
const contentType = ref('')
const sourceType = ref('')
const items = ref<FeedItem[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(true)
const offset = ref(0)
const limit = 20
/** Drop stale feed responses when tab/filter races mid-flight. */
let feedLoadSeq = 0
/** Prefer my-updates once after login; don't thrash tab on every onShow. */
const didPreferUpdates = ref(false)

const emptyHint = computed(() => {
  if (tab.value === 'updates') {
    if (filter.value === 'unread') return '没有未读更新'
    if (filter.value === 'starred') return '还没有星标论文'
    if (filter.value === 'later') return '稍后再看列表为空'
    return '暂无更新，去订阅期刊或关键词吧'
  }
  if (contentType.value || sourceType.value) return '当前筛选下暂无文章'
  return '暂无文章'
})

// Tab page stays alive; re-sync when returning from login or other tabs.
onShow(() => {
  if (auth.isLoggedIn) {
    if (!didPreferUpdates.value) {
      tab.value = 'updates'
      didPreferUpdates.value = true
    }
  } else if (tab.value === 'updates') {
    tab.value = 'all'
  }
  resetAndFetch()
})

onPullDownRefresh(async () => {
  try {
    items.value = []
    offset.value = 0
    hasMore.value = true
    loadingMore.value = false
    await fetchItems()
  } finally {
    uni.stopPullDownRefresh()
  }
})


function goJournals() {
  if (loading.value) return
  uni.switchTab({ url: '/pages/journals/index' })
}

function goSubscriptions() {
  if (loading.value) return
  uni.switchTab({ url: '/pages/subscriptions/index' })
}

function switchTab(t: 'all' | 'updates') {
  if (loading.value || tab.value === t) return
  tab.value = t
  filter.value = ''
  contentType.value = ''
  sourceType.value = ''
  resetAndFetch()
}

function setFilter(f: string) {
  if (loading.value) return
  filter.value = filter.value === f ? '' : f
  resetAndFetch()
}

function clearFilter() {
  if (loading.value) return
  filter.value = ''
  resetAndFetch()
}

function clearContentType() {
  if (loading.value) return
  contentType.value = ''
  sourceType.value = ''
  resetAndFetch()
}

function setContentType(t: string) {
  if (loading.value) return
  contentType.value = contentType.value === t ? '' : t
  resetAndFetch()
}

function setSourceType(t: string) {
  if (loading.value) return
  sourceType.value = sourceType.value === t ? '' : t
  resetAndFetch()
}

function resetAndFetch() {
  items.value = []
  offset.value = 0
  hasMore.value = true
  fetchItems()
}

async function fetchItems(isLoadMore = false) {
  if (isLoadMore) {
    if (!hasMore.value || loadingMore.value || loading.value) return
    loadingMore.value = true
  } else {
    loading.value = true
  }
  const seq = ++feedLoadSeq
  try {
    if (tab.value === 'updates' && auth.isLoggedIn) {
      const res = await getMyUpdates({
        limit,
        offset: offset.value,
        filter: filter.value || undefined,
      })
      if (seq !== feedLoadSeq) return
      const mapped: FeedItem[] = res.updates.map(u => ({
        id: u.article_id,
        title: u.title,
        authors: u.authors || [],
        journal_id: u.journal_id,
        journal_name: u.journal_name || '',
        publish_date: u.publish_date ?? null,
        content_type: u.content_type || 'journal',
        journal_source_type: u.journal_source_type || undefined,
        reasons: u.reasons || [],
        unread: !u.status?.is_read,
        abstract: u.abstract || '',
        doi: u.doi,
        url: u.url || '',
        original_url: u.original_url || '',
      }))
      items.value.push(...mapped)
      offset.value += res.updates.length
      hasMore.value = typeof res.total === 'number'
        ? items.value.length < res.total
        : res.updates.length === limit
    } else {
      const res = await getArticles({
        limit,
        offset: offset.value,
        content_type: contentType.value || undefined,
        source_type: sourceType.value || undefined,
      })
      if (seq !== feedLoadSeq) return
      const mapped: FeedItem[] = res.articles.map(a => ({
        id: a.id,
        title: a.title,
        authors: a.authors || [],
        journal_id: a.journal_id,
        journal_name: a.journal_name || '',
        publish_date: a.publish_date ?? null,
        content_type: a.content_type || 'journal',
        journal_source_type: a.journal_source_type || undefined,
        reasons: [],
        abstract: a.abstract || '',
        doi: a.doi,
        url: a.url || '',
      }))
      items.value.push(...mapped)
      offset.value += res.articles.length
      const total = typeof res.total === 'number' ? res.total : undefined
      hasMore.value = total != null
        ? items.value.length < total
        : res.articles.length === limit
    }
  } catch (e: any) {
    if (seq !== feedLoadSeq) return
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    if (seq === feedLoadSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function loadMore() {
  fetchItems(true)
}

const originalClickBusy = ref(new Set<string>())

function goDetail(id: string) {
  if (loading.value) return
  if (originalClickBusy.value.has(id)) return
  uni.navigateTo({ url: `/pages/article/detail?id=${id}` })
}

function goJournal(id?: string, articleId?: string) {
  if (loading.value) return
  if (articleId && originalClickBusy.value.has(articleId)) return
  if (!id) return
  uni.navigateTo({ url: `/pages/journals/detail?id=${id}` })
}

async function copyLink(url: string, item?: FeedItem) {
  if (loading.value) return
  if (!url) return
  if (item?.id && originalClickBusy.value.has(item.id)) return
  if (auth.isLoggedIn && item?.id) {
    originalClickBusy.value = new Set([...originalClickBusy.value, item.id])
    try {
      await recordOriginalClick(item.id)
      // My-updates items carry unread; plaza "all" cards lack status — still mark once.
      if (item.unread !== false) {
        await updateArticleStatus(item.id, { is_read: true })
        item.unread = false
      }
    } catch {
      // non-blocking
    } finally {
      const next = new Set(originalClickBusy.value)
      next.delete(item.id)
      originalClickBusy.value = next
    }
  }
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '链接已复制', icon: 'none' }),
  })
}
onUnload(() => { feedLoadSeq++ })
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; flex-wrap: wrap; padding: 20rpx 30rpx; gap: 24rpx; background: #f8f8f8; }
.tabs-busy { opacity: 0.55; pointer-events: none; }
.tab { font-size: 28rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-empty { margin-top: 24rpx; background: #e8f8e0; color: #3cc51f; border: none; }
.btn-empty.ghost { background: #fff; border: 2rpx solid #3cc51f; }
.scroll-view { height: calc(100vh - 100rpx); }
.loading-more { text-align: center; padding: 20rpx; color: #999; font-size: 26rpx; }
.card { background: #fff; padding: 28rpx 30rpx; border-bottom: 1rpx solid #f0f0f0; }
.meta { display: flex; flex-wrap: wrap; gap: 12rpx; margin-bottom: 8rpx; align-items: center; }
.journal { font-size: 24rpx; color: #3cc51f; }
.journal.link { text-decoration: underline; text-underline-offset: 4rpx; }
.journal.link.busy { opacity: 0.45; pointer-events: none; }
.badge { font-size: 20rpx; background: #eef6ff; color: #3a7bd5; padding: 2rpx 10rpx; border-radius: 6rpx; }
.badge.source { color: #666; background: #f0f0f0; }
.badge.reason { background: #fff7e6; color: #d48806; }
.title { font-size: 30rpx; color: #333; line-height: 1.4; display: block; }
.title.unread { font-weight: 600; }
.authors { font-size: 24rpx; color: #888; margin-top: 8rpx; display: block; }
.date { font-size: 22rpx; color: #aaa; margin-top: 6rpx; display: block; }
.snippet { font-size: 24rpx; color: #999; margin-top: 10rpx; display: block; line-height: 1.5; }
.actions { display: flex; gap: 24rpx; margin-top: 12rpx; }
.action-link { font-size: 24rpx; color: #3cc51f; }
.action-link.disabled { opacity: 0.45; pointer-events: none; }
button:disabled { opacity: 0.55; }
.card.busy { opacity: 0.55; pointer-events: none; }
</style>
