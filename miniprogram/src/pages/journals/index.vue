<template>
  <view class="container">
    <view class="search-bar">
      <view class="title-row">
        <text class="page-title">期刊广场</text>
        <text v-if="!loading" class="count-badge">{{ total || journals.length }} 源</text>
      </view>
      <input class="search-input" v-model="search" placeholder="搜索名称 / 描述 / slug" confirm-type="search" @confirm="reload" />
      <view class="filters">
        <text :class="['chip', contentType === '' && 'on']" @click="setType('')">全部</text>
        <text :class="['chip', contentType === 'journal' && 'on']" @click="setType('journal')">{{ contentTypeLabel('journal') }}</text>
        <text :class="['chip', contentType === 'preprint' && 'on']" @click="setType('preprint')">{{ contentTypeLabel('preprint') }}</text>
      </view>
      <view class="filters">
        <text :class="['chip', sourceType === '' && 'on']" @click="setSource('')">全部源</text>
        <text :class="['chip', sourceType === 'rss' && 'on']" @click="setSource('rss')">{{ sourceTypeLabel('rss') }}</text>
        <text :class="['chip', sourceType === 'arxiv' && 'on']" @click="setSource('arxiv')">{{ sourceTypeLabel('arxiv') }}</text>
        <text :class="['chip', sourceType === 'cnki' && 'on']" @click="setSource('cnki')">{{ sourceTypeLabel('cnki') }}</text>
      </view>
      <view class="filters">
        <text :class="['chip', sortBy === 'name' && 'on']" @click="sortBy = 'name'">名称</text>
        <text :class="['chip', sortBy === 'articles' && 'on']" @click="sortBy = 'articles'">论文数</text>
        <text :class="['chip', sortBy === 'updated' && 'on']" @click="sortBy = 'updated'">最近更新</text>
      </view>
      <view v-if="majorOptions.length" class="filters cas-row">
        <text class="cas-label">CAS{{ casYear != null ? ` ${casYear}` : '' }}</text>
        <text :class="['chip', major === '' && 'on']" @click="setMajor('')">全部大类</text>
        <text
          v-for="m in majorOptions"
          :key="m"
          :class="['chip', major === m && 'on']"
          @click="setMajor(m)"
        >{{ m }}</text>
      </view>
      <view v-if="major" class="filters">
        <text :class="['chip', zone === '' && 'on']" @click="setZone('')">全部区</text>
        <text
          v-for="z in zoneOptions"
          :key="z"
          :class="['chip', zone === String(z) && 'on']"
          @click="setZone(String(z))"
        >{{ z }}区</text>
        <text :class="['chip', topOnly && 'on']" @click="toggleTop">Top</text>
      </view>
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="!total && !journals.length" class="empty">
      <text>{{ emptyHint }}</text>
      <button v-if="hasActiveFilters" size="mini" class="btn-empty" @click="clearFilters">清除筛选</button>
      <button v-else size="mini" class="btn-empty" @click="goEmptyCta">{{ emptyCtaLabel }}</button>
    </view>
    <scroll-view v-else scroll-y class="scroll-view" @scrolltolower="loadMore">
      <JournalCard v-for="j in journals" :key="j.id" :journal="j" />
      <view v-if="loadingMore" class="loading-more"><text>加载中...</text></view>
      <view v-else-if="hasMore" class="loading-more"><text>上拉加载更多</text></view>
      <view v-else-if="journals.length" class="loading-more"><text>已显示全部</text></view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { getJournals, type Journal } from '@/api/journals'
import { getCasCategories, type CasCategory } from '@/api/categories'
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { contentTypeLabel, sourceTypeLabel } from '@/utils/format'
import JournalCard from '@/components/JournalCard.vue'

const auth = useAuthStore()
const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')
const contentType = ref('')
const sourceType = ref('')
const sortBy = ref<'name' | 'articles' | 'updated'>('name')
const major = ref('')
const zone = ref('')
const topOnly = ref(false)
const casYear = ref<number | null>(null)
const casCategories = ref<CasCategory[]>([])
const pageSize = 30
const offset = ref(0)
const total = ref(0)
const loadingMore = ref(false)
const hasMore = computed(() => journals.value.length < total.value)
/** Drop stale plaza list responses when filters race mid-flight. */
let journalsLoadSeq = 0
let casLoaded = false

const majorOptions = computed(() => {
  const set = new Set(casCategories.value.map((c) => c.major).filter(Boolean))
  return [...set].sort()
})
const zoneOptions = [1, 2, 3, 4]

const hasActiveFilters = computed(() =>
  Boolean(
    search.value.trim()
    || contentType.value
    || sourceType.value
    || major.value
    || zone.value
    || topOnly.value,
  ),
)
const emptyHint = computed(() =>
  hasActiveFilters.value ? '当前筛选下暂无期刊' : '暂无期刊',
)
const emptyCtaLabel = computed(() =>
  auth.isLoggedIn ? '去添加源' : '登录后添加源',
)

function listParams(extra: { limit?: number; offset?: number } = {}) {
  const hasCas = Boolean(major.value || zone.value || topOnly.value)
  return {
    q: search.value.trim() || undefined,
    content_type: contentType.value || undefined,
    source_type: sourceType.value || undefined,
    major: major.value || undefined,
    zone: zone.value || undefined,
    top: topOnly.value ? 'true' : undefined,
    year: hasCas && casYear.value != null ? casYear.value : undefined,
    sort: sortBy.value,
    limit: extra.limit ?? pageSize,
    offset: extra.offset ?? 0,
  }
}

function setType(t: string) {
  if (loading.value) return
  contentType.value = t
  reload()
}

function setSource(t: string) {
  if (loading.value) return
  sourceType.value = t
  reload()
}

function setMajor(m: string) {
  if (loading.value) return
  major.value = m
  if (!m) {
    zone.value = ''
    topOnly.value = false
  }
  reload()
}

function setZone(z: string) {
  if (loading.value) return
  zone.value = z
  reload()
}

function toggleTop() {
  if (loading.value) return
  topOnly.value = !topOnly.value
  reload()
}

function clearFilters() {
  if (loading.value) return
  search.value = ''
  contentType.value = ''
  sourceType.value = ''
  major.value = ''
  zone.value = ''
  topOnly.value = false
  reload()
}

async function ensureCasFacets() {
  if (casLoaded) return
  try {
    const cas = await getCasCategories()
    const years = cas.years?.length
      ? cas.years
      : [...new Set(cas.categories.map((c) => c.year))].sort((a, b) => b - a)
    const latest = years[0]
    if (latest != null) {
      casYear.value = latest
      const scoped = await getCasCategories({ year: latest })
      casCategories.value = scoped.categories
    } else {
      casCategories.value = cas.categories
    }
    casLoaded = true
  } catch {
    // CAS facets are optional; list still works without them.
  }
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value) return
  const seq = ++journalsLoadSeq
  loadingMore.value = true
  try {
    const res = await getJournals(listParams({ offset: offset.value }))
    if (seq !== journalsLoadSeq) return
    journals.value = [...journals.value, ...res.journals]
    offset.value += res.journals.length
    total.value = typeof res.total === 'number' ? res.total : journals.value.length
  } catch (e: any) {
    if (seq !== journalsLoadSeq) return
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    if (seq === journalsLoadSeq) loadingMore.value = false
  }
}

async function reload() {
  const seq = ++journalsLoadSeq
  loading.value = true
  offset.value = 0
  try {
    const res = await getJournals(listParams({ offset: 0 }))
    if (seq !== journalsLoadSeq) return
    journals.value = res.journals
    offset.value = res.journals.length
    total.value = typeof res.total === 'number' ? res.total : res.journals.length
  } catch (e: any) {
    if (seq !== journalsLoadSeq) return
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    if (seq === journalsLoadSeq) loading.value = false
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
  if (loading.value) return
  reload()
})

onShow(async () => {
  await ensureCasFacets()
  reload()
})

onPullDownRefresh(async () => {
  try {
    casLoaded = false
    await ensureCasFacets()
    await reload()
  } finally {
    uni.stopPullDownRefresh()
  }
})
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
.filters {
  display: flex; gap: 16rpx; margin-top: 16rpx; flex-wrap: wrap; align-items: center;
}
.cas-row { max-height: 140rpx; overflow-y: auto; }
.cas-label { font-size: 22rpx; color: #888; flex-shrink: 0; }
.chip {
  font-size: 24rpx; padding: 8rpx 20rpx; border-radius: 24rpx;
  background: #fff; color: #666; border: 1rpx solid #eee;
}
.chip.on { background: #e8f8e0; color: #3cc51f; border-color: #3cc51f; }
.loading, .empty { text-align: center; padding: 100rpx 40rpx; color: #999; }
.btn-empty { margin-top: 24rpx; background: #e8f8e0; color: #3cc51f; border: none; }
.scroll-view { height: calc(100vh - 360rpx); }
.loading-more { text-align: center; padding: 24rpx; color: #999; font-size: 24rpx; }
</style>
