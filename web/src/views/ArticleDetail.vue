<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <div v-if="loading"><n-spin /></div>
  <template v-else-if="article">
    <div style="margin-bottom: 12px;">
      <router-link v-if="article.journal_name" :to="`/journals/${article.journal_id}`" style="text-decoration: none;">
        <n-tag :bordered="false" style="margin-right: 6px;">{{ article.journal_name }}</n-tag>
      </router-link>
      <n-tag v-if="article.content_type === 'preprint'" type="info" size="small" :bordered="false" style="margin-right: 6px;">
        预印本
      </n-tag>
      <n-tag :type="article.journal_source_type === 'arxiv' ? 'info' : 'success'" size="small" :bordered="false">
        {{ article.journal_source_type }}
      </n-tag>
    </div>

    <n-h2>{{ article.title }}</n-h2>

    <n-descriptions label-placement="left" :column="2" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="作者">
        {{ article.authors?.join(', ') || '未知' }}
      </n-descriptions-item>
      <n-descriptions-item label="发表日期">
        {{ article.publish_date || '未知' }}
      </n-descriptions-item>
      <n-descriptions-item label="DOI">
        <a v-if="article.doi" :href="doiUrl(article.doi)" target="_blank">{{ article.doi }}</a>
        <span v-else>-</span>
      </n-descriptions-item>
      <n-descriptions-item label="原文链接">
        <a v-if="article.url" :href="article.url" target="_blank" @click="onOriginalClick">{{ article.url.slice(0, 60) }}...</a>
        <span v-else>-</span>
      </n-descriptions-item>
      <n-descriptions-item label="抓取时间">
        {{ formatDate(article.fetched_at) }}
      </n-descriptions-item>
    </n-descriptions>

    <n-h4>摘要</n-h4>
    <p style="line-height: 1.8; white-space: pre-wrap;">{{ cleanAbstract(article.abstract) }}</p>

    <div style="margin-top: 20px; display: flex; flex-wrap: wrap; gap: 12px;">
      <n-button type="primary" tag="a" :href="article.url" target="_blank" @click="onOriginalClick">
        查看原文
      </n-button>
      <n-button v-if="article.doi" quaternary tag="a" :href="doiUrl(article.doi)" target="_blank" @click="onOriginalClick">
        DOI 原文
      </n-button>
      <template v-if="isLoggedIn">
        <n-button :type="status.is_read ? 'success' : 'default'" ghost @click="toggle('is_read')" :loading="statusSaving">
          {{ status.is_read ? '已读' : '标为已读' }}
        </n-button>
        <n-button :type="status.is_starred ? 'warning' : 'default'" ghost @click="toggle('is_starred')" :loading="statusSaving">
          {{ status.is_starred ? '已星标' : '星标' }}
        </n-button>
        <n-button :type="status.is_later ? 'info' : 'default'" ghost @click="toggle('is_later')" :loading="statusSaving">
          {{ status.is_later ? '稍后再看中' : '稍后再看' }}
        </n-button>
      </template>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import { getArticleStatus, updateArticleStatus, recordOriginalClick, type ArticleStatus } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import {
  NH2, NH4, NButton, NSpin, NTag,
  NDescriptions, NDescriptionsItem, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)
const article = ref<Article | null>(null)
const loading = ref(true)
const statusSaving = ref(false)
const status = ref<ArticleStatus>({
  user_id: '',
  article_id: '',
  is_read: false,
  is_starred: false,
  is_later: false,
  original_clicked_at: null,
})

function doiUrl(doi: string): string {
  if (doi.startsWith('http')) return doi
  return `https://doi.org/${doi}`
}

function formatDate(d: string): string {
  return d.slice(0, 10)
}

function cleanAbstract(text: string): string {
  return text.replace(/^arXiv:\S+ Announce Type: \S+\s*\n\s*Abstract:\s*/i, '')
}

async function toggle(field: 'is_read' | 'is_starred' | 'is_later') {
  if (!article.value) return
  statusSaving.value = true
  try {
    status.value = await updateArticleStatus(article.value.id, { [field]: !status.value[field] })
  } catch (e: any) {
    message.error(e.message || '更新失败')
  } finally {
    statusSaving.value = false
  }
}

async function onOriginalClick() {
  if (!isLoggedIn.value || !article.value) return
  try {
    await recordOriginalClick(article.value.id)
    if (!status.value.is_read) {
      status.value = await updateArticleStatus(article.value.id, { is_read: true })
    }
  } catch {
    // non-blocking
  }
}

onMounted(async () => {
  const id = route.params.id as string
  try {
    article.value = await getArticle(id)
    if (isLoggedIn.value) {
      try {
        status.value = await getArticleStatus(id)
        if (!status.value.is_read) {
          status.value = await updateArticleStatus(id, { is_read: true })
        }
      } catch {
        // status optional
      }
    }
  } finally {
    loading.value = false
  }
})
</script>
