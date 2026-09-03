<template>
  <view class="container">
    <view v-if="loading" class="loading"><text>加载中...</text></view>
    <view v-else-if="loadError" class="empty">
      <text>{{ loadError }}</text>
      <button size="mini" class="btn-back" @click="goBack">返回</button>
    </view>
    <template v-else-if="article">
      <view class="journal-name">
        <text
          v-if="article.journal_id"
          class="journal-link"
          @click="goJournal"
        >{{ article.journal_name }}</text>
        <text v-else>{{ article.journal_name }}</text>
        <text v-if="article.content_type === 'preprint'" class="tag preprint">预印本</text>
      </view>
      <text class="title">{{ article.title }}</text>
      <text class="authors" v-if="article.authors?.length">
        {{ article.authors.join(', ') }}
      </text>
      <text class="date" v-if="article.publish_date">
        {{ formatDate(article.publish_date) }}
      </text>

      <view class="section" v-if="article.abstract">
        <text class="section-title">摘要</text>
        <text class="abstract">{{ cleanAbstract(article.abstract) }}</text>
      </view>

      <view class="status-row" v-if="auth.isLoggedIn">
        <text :class="['chip', status.is_read && 'on']" @click="toggle('is_read')">{{ status.is_read ? '已读' : '标已读' }}</text>
        <text :class="['chip', status.is_starred && 'on']" @click="toggle('is_starred')">{{ status.is_starred ? '已星标' : '星标' }}</text>
        <text :class="['chip', status.is_later && 'on']" @click="toggle('is_later')">{{ status.is_later ? '稍后再看' : '稍后' }}</text>
      </view>

      <view class="actions">
        <button class="btn-link" v-if="article.doi" @click="openOriginal(`https://doi.org/${article.doi}`)">
          查看原文
        </button>
        <button class="btn-link" v-else-if="article.url" @click="openOriginal(article.url)">
          查看原文
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getArticle, type Article } from '@/api/articles'
import {
  getArticleStatus,
  updateArticleStatus,
  recordOriginalClick,
  type ArticleStatus,
} from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/format'

const auth = useAuthStore()
const article = ref<Article | null>(null)
const loading = ref(true)
const loadError = ref('')
const status = ref<ArticleStatus>({
  user_id: '',
  article_id: '',
  is_read: false,
  is_starred: false,
  is_later: false,
  original_clicked_at: null,
})

function cleanAbstract(text?: string): string {
  if (!text) return ''
  return text.replace(/^arXiv:\S+ Announce Type: \S+\s*\n\s*Abstract:\s*/i, '')
}

function goBack() {
  uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/index/index' }) })
}

function goJournal() {
  const id = article.value?.journal_id
  if (!id) return
  uni.navigateTo({ url: `/pages/journals/detail?id=${id}` })
}

onMounted(async () => {
  const pages = getCurrentPages()
  const page = pages[pages.length - 1] as any
  const id = page.$page?.options?.id || page.options?.id
  if (!id) {
    loadError.value = '缺少文章 ID'
    loading.value = false
    return
  }

  try {
    article.value = await getArticle(id)
    if (auth.isLoggedIn) {
      try {
        status.value = await getArticleStatus(id)
        if (!status.value.is_read) {
          status.value = await updateArticleStatus(id, { is_read: true })
        }
      } catch {
        // optional
      }
    }
  } catch (e: any) {
    loadError.value = e?.message || '文章不存在或无权查看'
  } finally {
    loading.value = false
  }
})

async function toggle(field: 'is_read' | 'is_starred' | 'is_later') {
  if (!article.value || !auth.isLoggedIn) return
  try {
    status.value = await updateArticleStatus(article.value.id, {
      [field]: !status.value[field],
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '更新失败', icon: 'none' })
  }
}

async function openOriginal(url: string) {
  if (auth.isLoggedIn && article.value) {
    try {
      await recordOriginalClick(article.value.id)
    } catch {
      // non-blocking
    }
  }
  uni.setClipboardData({ data: url, success: () => uni.showToast({ title: '链接已复制', icon: 'none' }) })
}
</script>

<style scoped>
.container { padding: 30rpx; }
.journal-name { font-size: 26rpx; color: #3cc51f; display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.journal-link { color: #3cc51f; text-decoration: underline; text-underline-offset: 4rpx; }
.tag { font-size: 22rpx; color: #3cc51f; background: #e8f8e0; padding: 4rpx 12rpx; border-radius: 8rpx; }
.tag.preprint { color: #2080f0; background: #e8f3ff; }
.title { font-size: 36rpx; font-weight: 600; color: #333; line-height: 1.5; margin-top: 16rpx; display: block; }
.authors { font-size: 28rpx; color: #666; margin-top: 12rpx; display: block; }
.date { font-size: 26rpx; color: #999; margin-top: 8rpx; display: block; }
.section { margin-top: 40rpx; }
.section-title { font-size: 30rpx; font-weight: 500; display: block; margin-bottom: 12rpx; }
.abstract { font-size: 28rpx; color: #444; line-height: 1.8; }
.status-row { display: flex; gap: 16rpx; margin-top: 36rpx; flex-wrap: wrap; }
.chip {
  font-size: 24rpx; padding: 10rpx 20rpx; border-radius: 8rpx;
  background: #f5f5f5; color: #666;
}
.chip.on { background: #e8f8e0; color: #3cc51f; }
.actions { margin-top: 40rpx; }
.btn-link {
  width: 100%; padding: 24rpx; background: #3cc51f; color: #fff;
  border: none; border-radius: 12rpx; font-size: 30rpx; text-align: center;
}
.loading, .empty { text-align: center; padding: 100rpx; color: #999; }
.btn-back { margin-top: 24rpx; }
</style>
