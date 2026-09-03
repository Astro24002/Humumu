<template>
  <view class="card" @click="goDetail">
    <view class="meta">
      <view class="meta-left">
        <text
          v-if="article.journal_id"
          class="journal link"
          @click.stop="goJournal"
        >{{ article.journal_name }}</text>
        <text v-else class="journal">{{ article.journal_name }}</text>
        <text v-if="article.content_type === 'preprint'" class="tag preprint">{{ contentTypeLabel(article.content_type) }}</text>
      </view>
      <text class="date">{{ formatDate(article.publish_date) }}</text>
    </view>
    <text class="title">{{ article.title }}</text>
    <text class="authors" v-if="article.authors?.length">
      {{ authorsLabel }}
    </text>
    <text class="abstract" v-if="article.abstract" line-clamp="2">
      {{ cleanAbstract(article.abstract) }}
    </text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Article } from '@/api/articles'
import { formatDate, formatAuthors, contentTypeLabel } from '@/utils/format'
import { cleanAbstract } from '@/utils/abstract'

const props = defineProps<{ article: Article }>()

const authorsLabel = computed(() => formatAuthors(props.article.authors || []))

function goDetail() {
  uni.navigateTo({ url: `/pages/article/detail?id=${props.article.id}` })
}

function goJournal() {
  if (!props.article.journal_id) return
  uni.navigateTo({ url: `/pages/journals/detail?id=${props.article.journal_id}` })
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
.meta { display: flex; justify-content: space-between; align-items: center; gap: 12rpx; margin-bottom: 12rpx; }
.meta-left { display: flex; align-items: center; gap: 10rpx; flex-wrap: wrap; min-width: 0; flex: 1; }
.journal { font-size: 24rpx; color: #3cc51f; }
.journal.link { text-decoration: underline; text-underline-offset: 4rpx; }
.tag { font-size: 20rpx; padding: 2rpx 10rpx; border-radius: 8rpx; }
.tag.preprint { color: #2080f0; background: #e8f3ff; }
.date { font-size: 24rpx; color: #999; flex-shrink: 0; }
.title { font-size: 32rpx; font-weight: 500; color: #333; line-height: 1.5; }
.authors { font-size: 26rpx; color: #666; margin-top: 8rpx; display: block; }
.abstract { font-size: 26rpx; color: #999; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; }
</style>
