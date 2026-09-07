<template>
  <view class="card" :class="{ busy }" @click="goDetail">
    <view class="header">
      <text class="name">{{ journal.name }}</text>
      <view class="tags">
        <text v-if="journal.content_type === 'preprint'" class="tag preprint">{{ contentTypeLabel(journal.content_type) }}</text>
        <text class="tag">{{ sourceTypeLabel(journal.source_type) }}</text>
        <text v-if="journal.health_status === 'paused'" class="tag paused">{{ healthStatusLabel(journal.health_status) }}</text>
      </view>
    </view>
    <view class="stats">
      <text>论文 {{ journal.article_count ?? 0 }}</text>
      <text>更新 {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}</text>
    </view>
    <text v-if="journal.description" class="desc" line-clamp="2">{{ journal.description }}</text>
    <text v-if="linkLabel" class="link" @click.stop="openLink">{{ linkLabel }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Journal } from '@/api/journals'
import { formatDate, shortUrl, sourceTypeLabel, contentTypeLabel, healthStatusLabel } from '@/utils/format'

const props = defineProps<{ journal: Journal; busy?: boolean }>()

const linkUrl = computed(() => props.journal.homepage_url || props.journal.source_url || '')

const linkLabel = computed(() => shortUrl(linkUrl.value))

function goDetail() {
  if (props.busy) return
  uni.navigateTo({ url: `/pages/journals/detail?id=${props.journal.id}` })
}

function openLink() {
  if (props.busy) return
  const url = linkUrl.value
  if (!url) return
  // #ifdef H5
  window.open(url, '_blank')
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '链接已复制', icon: 'none' }),
  })
  // #endif
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
.header { display: flex; justify-content: space-between; align-items: center; gap: 12rpx; }
.name { font-size: 32rpx; font-weight: 500; flex: 1; min-width: 0; }
.tags { display: flex; gap: 8rpx; flex-shrink: 0; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag.preprint { color: #2080f0; background: #e8f3ff; }
.tag.paused { color: #d03050; background: #fdecef; }
.stats { display: flex; gap: 30rpx; font-size: 26rpx; color: #999; margin-top: 16rpx; }
.desc { font-size: 26rpx; color: #666; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; }
.link { font-size: 22rpx; color: #18a058; margin-top: 10rpx; display: block; }
.card.busy { opacity: 0.55; pointer-events: none; }
</style>
