<template>
  <view class="container">
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <template v-else-if="article">
      <view class="journal-name">{{ article.journal_name }}</view>
      <text class="title">{{ article.title }}</text>
      <text class="authors" v-if="article.authors?.length">
        {{ article.authors.join(', ') }}
      </text>
      <text class="date" v-if="article.publish_date">
        {{ formatDate(article.publish_date) }}
      </text>

      <view class="section" v-if="article.abstract">
        <text class="section-title">摘要</text>
        <text class="abstract">{{ article.abstract }}</text>
      </view>

      <view class="actions">
        <button class="btn-link" v-if="article.doi" @click="openURL(`https://doi.org/${article.doi}`)">
          查看原文
        </button>
        <button class="btn-link" v-else-if="article.url" @click="openURL(article.url)">
          查看原文
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getArticle, type Article } from '@/api/articles'
import { formatDate } from '@/utils/format'

const article = ref<Article | null>(null)
const loading = ref(true)

onMounted(async () => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  const id = page.$page?.options?.id || page.options?.id
  if (!id) return

  try {
    const res = await getArticle(id)
    article.value = res.article
  } finally {
    loading.value = false
  }
})

function openURL(url: string) {
  uni.setClipboardData({ data: url, success: () => uni.showToast({ title: '链接已复制', icon: 'none' }) })
}
</script>

<style scoped>
.container { padding: 30rpx; }
.journal-name { font-size: 26rpx; color: #3cc51f; }
.title { font-size: 36rpx; font-weight: 600; color: #333; line-height: 1.5; margin-top: 16rpx; display: block; }
.authors { font-size: 28rpx; color: #666; margin-top: 12rpx; display: block; }
.date { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
.section { margin-top: 40rpx; }
.section-title { font-size: 30rpx; font-weight: 500; display: block; margin-bottom: 12rpx; }
.abstract { font-size: 28rpx; color: #444; line-height: 1.8; }
.actions { margin-top: 50rpx; }
.btn-link {
  width: 100%; padding: 24rpx; background: #3cc51f; color: #fff;
  border: none; border-radius: 12rpx; font-size: 30rpx; text-align: center;
}
.loading { text-align: center; padding: 100rpx; color: #999; }
</style>
