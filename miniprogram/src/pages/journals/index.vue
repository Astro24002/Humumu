<template>
  <view class="container">
    <view class="search-bar">
      <view class="title-row">
        <text class="page-title">期刊广场</text>
        <text v-if="!loading" class="count-badge">{{ journals.length }} 源</text>
      </view>
      <input class="search-input" v-model="search" placeholder="搜索名称 / 描述 / slug" confirm-type="search" @confirm="reload" />
      <view class="filters">
        <text :class="['chip', contentType === '' && 'on']" @click="setType('')">全部</text>
        <text :class="['chip', contentType === 'journal' && 'on']" @click="setType('journal')">期刊</text>
        <text :class="['chip', contentType === 'preprint' && 'on']" @click="setType('preprint')">预印本</text>
      </view>
      <view class="filters">
        <text :class="['chip', sortBy === 'name' && 'on']" @click="sortBy = 'name'">名称</text>
        <text :class="['chip', sortBy === 'articles' && 'on']" @click="sortBy = 'articles'">论文数</text>
        <text :class="['chip', sortBy === 'updated' && 'on']" @click="sortBy = 'updated'">最近更新</text>
      </view>
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="journals.length === 0" class="empty">
      <text>{{ emptyHint }}</text>
      <button v-if="hasActiveFilters" size="mini" class="btn-empty" @click="clearFilters">清除筛选</button>
      <button v-else size="mini" class="btn-empty" @click="goEmptyCta">{{ emptyCtaLabel }}</button>
    </view>
    <scroll-view v-else scroll-y class="scroll-view" @scrolltolower="loadMore">
      <JournalCard v-for="j in visibleJournals" :key="j.id" :journal="j" />
      <view v-if="hasMore" class="loading-more"><text>上拉加载更多</text></view>
      <view v-else-if="displayedJournals.length > pageSize" class="loading-more"><text>已显示全部</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { getJournals, type Journal } from '@/api/journals'
import { useAuthStore } from '@/stores/auth'
import JournalCard from '@/components/JournalCard.vue'

const auth = useAuthStore()
const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')
const contentType = ref('')
const sortBy = ref<'name' | 'articles' | 'updated'>('name')
const pageSize = 30
const visibleCount = ref(pageSize)

const hasActiveFilters = computed(() => Boolean(search.value.trim() || contentType.value))
const emptyHint = computed(() =>
  hasActiveFilters.value ? '当前筛选下暂无期刊' : '暂无期刊',
)
const emptyCtaLabel = computed(() =>
  auth.isLoggedIn ? '去添加源' : '登录后添加源',
)

const displayedJournals = computed(() => {
  const list = [...journals.value]
  if (sortBy.value === 'articles') {
    list.sort((a, b) => (b.article_count || 0) - (a.article_count || 0) || a.name.localeCompare(b.name))
  } else if (sortBy.value === 'updated') {
    list.sort((a, b) => {
      const da = a.last_article_date || ''
      const db = b.last_article_date || ''
      return db.localeCompare(da) || a.name.localeCompare(b.name)
    })
  } else {
    list.sort((a, b) => a.name.localeCompare(b.name))
  }
  return list
})

const visibleJournals = computed(() => displayedJournals.value.slice(0, visibleCount.value))
const hasMore = computed(() => visibleCount.value < displayedJournals.value.length)

function setType(t: string) {
  contentType.value = t
  reload()
}

function clearFilters() {
  search.value = ''
  contentType.value = ''
  reload()
}

function loadMore() {
  if (!hasMore.value) return
  visibleCount.value = Math.min(visibleCount.value + pageSize, displayedJournals.value.length)
}

async function reload() {
  loading.value = true
  visibleCount.value = pageSize
  try {
    journals.value = (await getJournals({
      q: search.value.trim() || undefined,
      content_type: contentType.value || undefined,
    })).journals
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function goEmptyCta() {
  if (auth.isLoggedIn) {
    uni.switchTab({ url: '/pages/subscriptions/index' })
  } else {
    goLogin()
  }
}

watch(sortBy, () => {
  visibleCount.value = pageSize
})

onMounted(reload)

// Keep catalog fresh when switching back to this tab.
onShow(() => {
  reload()
})

onPullDownRefresh(async () => {
  try {
    await reload()
  } finally {
    uni.stopPullDownRefresh()
  }
})
function goLogin() {
  const pages = getCurrentPages()
  const cur = pages[pages.length - 1] as any
  let from = ''
  if (cur) {
    const route = String(cur.route || '').replace(/^\/+/, '')
    const opts = cur.options || {}
    const qs = Object.keys(opts)
      .filter((k) => opts[k] != null && opts[k] !== '')
      .map((k) => `${k}=${encodeURIComponent(String(opts[k]))}`)
      .join('&')
    const fullPath = cur.$page && cur.$page.fullPath
      ? String(cur.$page.fullPath).replace(/^\/+/, '')
      : ''
    if (fullPath) {
      from = fullPath.startsWith('pages/') ? fullPath : `pages/${fullPath}`
    } else if (route) {
      const base = route.startsWith('pages/') ? route : `pages/${route}`
      from = qs ? `${base}?${qs}` : base
    }
  }
  const q = from ? `?from=${encodeURIComponent(from)}` : ''
  uni.navigateTo({ url: `/pages/login/index${q}` })
}
</script>

<style scoped>
.container { min-height: 100vh; }
.search-bar { padding: 16rpx 30rpx; background: #f8f8f8; }
.title-row { display: flex; align-items: center; gap: 16rpx; margin-bottom: 16rpx; }
.page-title { font-size: 32rpx; font-weight: 600; color: #333; }
.count-badge {
  font-size: 22rpx; color: #666; background: #eee; padding: 4rpx 14rpx;
  border-radius: 20rpx;
}
.search-input {
  background: #fff;
  border-radius: 40rpx;
  padding: 16rpx 30rpx;
  font-size: 28rpx;
  border: 1rpx solid #eee;
}
.filters { display: flex; gap: 16rpx; margin-top: 16rpx; }
.chip {
  font-size: 24rpx; padding: 8rpx 20rpx; border-radius: 24rpx;
  background: #fff; color: #666; border: 1rpx solid #eee;
}
.chip.on { background: #e8f8e0; color: #3cc51f; border-color: #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx 40rpx; color: #999; }
.btn-empty { margin-top: 24rpx; background: #e8f8e0; color: #3cc51f; border: none; }
.scroll-view { height: calc(100vh - 280rpx); }
.loading-more { text-align: center; padding: 24rpx; color: #999; font-size: 24rpx; }
</style>
