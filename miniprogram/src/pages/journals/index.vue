<template>
  <view class="container">
    <view class="search-bar">
      <input class="search-input" v-model="search" placeholder="搜索期刊" @input="onSearch" />
    </view>
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="filtered.length === 0" class="empty"><text>暂无期刊</text></view>
    <scroll-view v-else scroll-y class="scroll-view">
      <JournalCard v-for="j in filtered" :key="j.id" :journal="j" />
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getJournals, type Journal } from '@/api/journals'
import JournalCard from '@/components/JournalCard.vue'

const journals = ref<Journal[]>([])
const loading = ref(true)
const search = ref('')

const filtered = computed(() => {
  if (!search.value) return journals.value
  const q = search.value.toLowerCase()
  return journals.value.filter(j => j.name.toLowerCase().includes(q))
})

onMounted(async () => {
  try {
    journals.value = (await getJournals()).journals
  } finally {
    loading.value = false
  }
})

function onSearch() { /* computed handles it */ }
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
.loading, .empty { text-align: center; padding: 100rpx; color: #999; }
.scroll-view { height: calc(100vh - 120rpx); }
</style>
