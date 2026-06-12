<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <n-h2 v-if="journal">{{ journal.name }}</n-h2>
  <n-tag v-if="journal" :type="journal.source_type === 'arxiv' ? 'info' : 'success'" size="small">
    {{ journal.source_type }}
  </n-tag>

  <n-divider />

  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!articles.length" description="暂无文章" />
  <n-list v-else>
    <n-list-item v-for="a in articles" :key="a.id">
      <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
        <template #footer><router-link :to="`/articles/${a.id}`">查看详情</router-link></template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { NH2, NButton, NTag, NDivider, NSpin, NEmpty, NList, NListItem, NThing } from 'naive-ui'

const route = useRoute()
const router = useRouter()
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    journal.value = await getJournal(route.params.id as string)
    const res = await getArticles({ journal_id: route.params.id as string, limit: '50' })
    articles.value = res.articles
  } finally {
    loading.value = false
  }
})
</script>
