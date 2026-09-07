<template>
  <view class="card" @click="goDetail">
    <view class="meta">
      <view class="meta-left">
        <text
          v-if="article.journal_id && article.journal_name"
          class="journal link"
          @click.stop="goJournal"
        >{{ article.journal_name }}</text>
        <text v-else-if="article.journal_name" class="journal">{{ article.journal_name }}</text>
        <text v-if="article.content_type === 'preprint'" class="tag preprint">{{ contentTypeLabel(article.content_type) }}</text>
        <text v-if="article.journal_source_type" class="tag source">{{ sourceTypeLabel(article.journal_source_type) }}</text>
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
    <view v-if="article.doi || article.url" class="actions" @click.stop>
      <text
        v-if="article.doi"
        class="action-link"
        :class="{ disabled: originalBusy }"
        @click="!originalBusy && copyLink(doiUrl(article.doi))"
      >DOI</text>
      <text
        v-if="article.url"
        class="action-link"
        :class="{ disabled: originalBusy }"
        @click="!originalBusy && copyLink(article.url)"
      >原文</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Article } from '@/api/articles'
import { recordOriginalClick, updateArticleStatus } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { formatDate, formatAuthors, contentTypeLabel, sourceTypeLabel, doiUrl } from '@/utils/format'
import { cleanAbstract } from '@/utils/abstract'

const props = defineProps<{ article: Article }>()
const auth = useAuthStore()
/** Module-level: shared across card instances (no status on Article payload). */
const knownReadIds = new Set<string>()
const originalClickBusyIds = ref(new Set<string>())

const authorsLabel = computed(() => formatAuthors(props.article.authors || []))
const originalBusy = computed(() => originalClickBusyIds.value.has(props.article.id))

function goDetail() {
  uni.navigateTo({ url: `/pages/article/detail?id=${props.article.id}` })
}

function goJournal() {
  if (!props.article.journal_id) return
  uni.navigateTo({ url: `/pages/journals/detail?id=${props.article.journal_id}` })
}

async function onOriginalClick() {
  const articleId = props.article.id
  if (!auth.isLoggedIn || !articleId || originalClickBusyIds.value.has(articleId)) return
  originalClickBusyIds.value = new Set([...originalClickBusyIds.value, articleId])
  try {
    await recordOriginalClick(articleId)
    if (!knownReadIds.has(articleId)) {
      await updateArticleStatus(articleId, { is_read: true })
      knownReadIds.add(articleId)
    }
  } catch {
    // non-blocking
  } finally {
    const next = new Set(originalClickBusyIds.value)
    next.delete(articleId)
    originalClickBusyIds.value = next
  }
}

function copyLink(url: string) {
  if (!url || originalBusy.value) return
  void onOriginalClick()
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '链接已复制', icon: 'none' }),
  })
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
.tag.source { color: #666; background: #f0f0f0; }
.tag.preprint { color: #2080f0; background: #e8f3ff; }
.date { font-size: 24rpx; color: #999; flex-shrink: 0; }
.title { font-size: 32rpx; font-weight: 500; color: #333; line-height: 1.5; }
.authors { font-size: 26rpx; color: #666; margin-top: 8rpx; display: block; }
.abstract { font-size: 26rpx; color: #999; margin-top: 12rpx; display: block; line-height: 1.5; overflow: hidden; text-overflow: ellipsis; }
.actions { display: flex; gap: 24rpx; margin-top: 16rpx; }
.action-link { font-size: 24rpx; color: #3cc51f; }
.action-link.disabled { opacity: 0.45; pointer-events: none; }
</style>
