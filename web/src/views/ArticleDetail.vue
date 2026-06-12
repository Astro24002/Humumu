<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <div v-if="loading"><n-spin /></div>
  <template v-else-if="article">
    <n-h2>{{ article.title }}</n-h2>
    <p style="color: #666; margin-bottom: 8px;">作者：{{ article.authors?.join(', ') }}</p>
    <p style="color: #888; font-size: 12px; margin-bottom: 16px;">
      DOI: {{ article.doi }} | 发表日期：{{ article.publish_date || '未知' }}
    </p>
    <n-divider />
    <n-h4>摘要</n-h4>
    <p style="line-height: 1.8; white-space: pre-wrap;">{{ article.abstract }}</p>
    <n-button type="primary" tag="a" :href="article.url" target="_blank" style="margin-top: 16px;">
      查看原文
    </n-button>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import { NH2, NH4, NButton, NDivider, NSpin } from 'naive-ui'

const route = useRoute()
const router = useRouter()
const article = ref<Article | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    article.value = await getArticle(route.params.id as string)
  } finally {
    loading.value = false
  }
})
</script>
