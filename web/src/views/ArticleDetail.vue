<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <div v-if="loading"><n-spin /></div>
  <template v-else-if="article">
    <div style="margin-bottom: 12px;">
      <router-link v-if="article.journal_name" :to="`/journals/${article.journal_id}`" style="text-decoration: none;">
        <n-tag :bordered="false" style="margin-right: 6px;">{{ article.journal_name }}</n-tag>
      </router-link>
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
        <a v-if="article.url" :href="article.url" target="_blank">{{ article.url.slice(0, 60) }}...</a>
        <span v-else>-</span>
      </n-descriptions-item>
      <n-descriptions-item label="抓取时间">
        {{ formatDate(article.fetched_at) }}
      </n-descriptions-item>
    </n-descriptions>

    <n-h4>摘要</n-h4>
    <p style="line-height: 1.8; white-space: pre-wrap;">{{ cleanAbstract(article.abstract) }}</p>

    <div style="margin-top: 20px; display: flex; gap: 12px;">
      <n-button type="primary" tag="a" :href="article.url" target="_blank">
        查看原文
      </n-button>
      <n-button v-if="article.doi" quaternary tag="a" :href="doiUrl(article.doi)" target="_blank">
        DOI 原文
      </n-button>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import {
  NH2, NH4, NButton, NDivider, NSpin, NTag,
  NDescriptions, NDescriptionsItem
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const article = ref<Article | null>(null)
const loading = ref(true)

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

onMounted(async () => {
  try {
    article.value = await getArticle(route.params.id as string)
  } finally {
    loading.value = false
  }
})
</script>
