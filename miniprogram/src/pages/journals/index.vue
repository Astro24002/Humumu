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
        <text :class="['chip', sortBy === 'name' && 'on']" @click="sortBy = 'name'">名称</text>
        <text :class="['chip', sortBy === 'articles' && 'on']" @click="sortBy = 'articles'">论文数</text>
        <text :class="['chip', sortBy === 'updated' && 'on']" @click="sortBy = 'updated'">最近更新</text>
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
import { useAuthStore } from '@/stores/auth'
import { goLogin } from '@/utils/nav'
import { contentTypeLabel } from '@/utils/format'
import JournalCard from '@/components/JournalCard.vue'

const auth = useAuthStore()
const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')
const contentType = ref('')
const sortBy = ref<'name' | 'articles' | 'updated'>('name')
const pageSize = 30
const offset = ref(0)
const total = ref(0)
const loadingMore = ref(false)
const hasMore = computed(() => journals.value.length < total.value)

const hasActiveFilters = computed(() => Boolean(search.value.trim() || contentType.value))
const emptyHint = computed(() =>
  hasActiveFilters.value ? '当前筛选下暂无期刊' : '暂无期刊',
)
const emptyCtaLabel = computed(() =>
  auth.isLoggedIn ? '去添加源' : '登录后添加源',
)

function listParams(extra: { limit?: number; offset?: number } = {}) {
  return {
    q: search.value.trim() || undefined,
    content_type: contentType.value || undefined,
    sort: sortBy.value,
    limit: extra.limit ?? pageSize,
    offset: extra.offset ?? 0,
  }
}

function setType(t: string) {
  contentType.value = t
  reload()
}

function clearFilters() {
  search.value = ''
  contentType.value = ''
  reload()
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value) return
  loadingMore.value = true
  try {
    const res = await getJournals(listParams({ offset: offset.value }))
    journals.value = [...journals.value, ...res.journals]
    offset.value += res.journals.length
    total.value = typeof res.total === 'number' ? res.total : journals.value.length
  } catch (e: any) {
    uni.showToast({ title: e.message || '加载失败', icon: 'none' })
  } finally {
    loadingMore.value = false
  }
}

async function reload() {
  loading.value = true
  offset.value = 0
  try {
    const res = await getJournals(listParams({ offset: 0 }))
    journals.value = res.journals
    offset.value = res.journals.length
    total.value = typeof res.total === 'number' ? res.total : res.journals.length
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
  reload()
})

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
