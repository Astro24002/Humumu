<template>
  <view class="card" @click="goDetail">
    <view class="meta">
      <text class="journal">{{ article.journal_name }}</text>
      <text class="date">{{ formatDate(article.publish_date) }}</text>
    </view>
    <text class="title">{{ article.title }}</text>
    <text class="authors" v-if="article.authors?.length">
      {{ article.authors.join(', ') }}
    </text>
    <text class="abstract" v-if="article.abstract" line-clamp="2">
      {{ cleanAbstract(article.abstract) }}
    </text>
  </view>
</template>

<script setup lang="ts">
import type { Article } from '@/api/articles'
import { formatDate } from '@/utils/format'

function cleanAbstract(text?: string): string {
  if (!text) return ''
  return text.replace(/^arXiv:\S+ Announce Type: \S+\s*\n\s*Abstract:\s*/i, '')
}

const props = defineProps<{ article: Article }>()

function goDetail() {
  uni.navigateTo({ url: `/pages/article/detail?id=${props.article.id}` })
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
.meta { display: flex; justify-content: space-between; margin-bottom: 12rpx; }
.journal { font-size: 24rpx; color: #3cc51f; }
.date { font-size: 24rpx; color: #999; }
.title { font-size: 32rpx; font-weight: 500; color: #333; line-height: 1.5; }
.authors { font-size: 26rpx; color: #666; margin-top: 8rpx; display: block; }
.abstract { font-size: 26rpx; color: #999; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; }
</style>
