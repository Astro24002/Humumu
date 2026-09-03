<template>
  <view class="container">
    <view class="search-bar">
      <input class="search-input" v-model="search" placeholder="搜索期刊" confirm-type="search" @confirm="reload" />
      <view class="filters">
        <text :class="['chip', contentType === '' && 'on']" @click="setType('')">全部</text>
        <text :class="['chip', contentType === 'journal' && 'on']" @click="setType('journal')">期刊</text>
        <text :class="['chip', contentType === 'preprint' && 'on']" @click="setType('preprint')">预印本</text>
      </view>
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="journals.length === 0" class="empty"><text>暂无期刊</text></view>
    <scroll-view v-else scroll-y class="scroll-view">
      <JournalCard v-for="j in journals" :key="j.id" :journal="j" />
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getJournals, type Journal } from '@/api/journals'
import JournalCard from '@/components/JournalCard.vue'

const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')
const contentType = ref('')

function setType(t: string) {
  contentType.value = t
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

onMounted(reload)
</script>

<style scoped>
.container { min-height: 100vh; }
.search-bar { padding: 16rpx 30rpx; background: #f8f8f8; }
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
.loading, .empty { text-align: center; padding: 100rpx; color: #999; }
.scroll-view { height: calc(100vh - 180rpx); }
</style>
