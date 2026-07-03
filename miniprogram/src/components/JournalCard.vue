<template>
  <view class="card" @click="goDetail">
    <view class="header">
      <text class="name">{{ journal.name }}</text>
      <text class="tag">{{ journal.source_type }}</text>
    </view>
    <view class="stats">
      <text>论文 {{ journal.article_count }}</text>
      <text>更新 {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}</text>
    </view>
    <text v-if="journal.description" class="desc" line-clamp="2">{{ journal.description }}</text>
  </view>
</template>

<script setup lang="ts">
import type { Journal } from '@/api/journals'
import { formatDate } from '@/utils/format'

const props = defineProps<{ journal: Journal }>()

function goDetail() {
  uni.navigateTo({ url: `/pages/journals/detail?id=${props.journal.id}` })
}
</script>

<style scoped>
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin: 16rpx 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.header { display: flex; justify-content: space-between; align-items: center; }
.name { font-size: 32rpx; font-weight: 500; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.stats { display: flex; gap: 30rpx; font-size: 26rpx; color: #999; margin-top: 16rpx; }
.desc { font-size: 26rpx; color: #666; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; }
</style>
