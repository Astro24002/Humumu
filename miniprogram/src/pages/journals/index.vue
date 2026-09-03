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
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="journals.length === 0" class="empty">
      <text>{{ emptyHint }}</text>
      <button v-if="hasActiveFilters" size="mini" class="btn-empty" @click="clearFilters">清除筛选</button>
      <button v-else size="mini" class="btn-empty" @click="goEmptyCta">{{ emptyCtaLabel }}</button>
    </view>
    <scroll-view v-else scroll-y class="scroll-view">
      <JournalCard v-for="j in journals" :key="j.id" :journal="j" />
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getJournals, type Journal } from '@/api/journals'
import { useAuthStore } from '@/stores/auth'
import JournalCard from '@/components/JournalCard.vue'

const auth = useAuthStore()
const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')
const contentType = ref('')

const hasActiveFilters = computed(() => Boolean(search.value.trim() || contentType.value))
const emptyHint = computed(() =>
  hasActiveFilters.value ? '当前筛选下暂无期刊' : '暂无期刊',
)
const emptyCtaLabel = computed(() =>
  auth.isLoggedIn ? '去添加源' : '登录后添加源',
)

function setType(t: string) {
  contentType.value = t
  reload()
}

function clearFilters() {
  search.value = ''
  contentType.value = ''
  reload()
}

async function reload() {
  loading.value = true
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
    uni.navigateTo({ url: '/pages/login/index' })
  }
}

onMounted(reload)
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
.scroll-view { height: calc(100vh - 180rpx); }
</style>
