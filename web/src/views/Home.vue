<template>
  <div>
    <n-h2>最新论文</n-h2>
    <n-select v-if="journals.length" v-model:value="filterJournalId" :options="journalOptions"
      placeholder="筛选期刊" clearable style="max-width: 300px; margin-bottom: 16px;" />

    <div v-if="loading"><n-spin /></div>
    <n-empty v-else-if="!articles.length" description="暂无文章" />

    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
          <template #footer>
            <router-link :to="`/articles/${a.id}`">查看详情</router-link>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>

    <n-pagination v-if="pageCount > 1" :page="page" :page-count="pageCount"
      @update:page="loadPage" style="margin-top: 16px;" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { getArticles, type Article } from '@/api/articles'
import { getJournals, type Journal } from '@/api/journals'
import { NH2, NSelect, NSpin, NEmpty, NList, NListItem, NThing, NPagination } from 'naive-ui'

const articles = ref<Article[]>([])
const journals = ref<Journal[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const limit = 20
const filterJournalId = ref<string | null>(null)

const pageCount = computed(() => Math.ceil(total.value / limit) || 1)

const journalOptions = computed(() =>
  journals.value.map(j => ({ label: j.name, value: j.id }))
)

async function loadArticles() {
  loading.value = true
  try {
    const params: Record<string, string> = {
      limit: String(limit),
      offset: String((page.value - 1) * limit),
    }
    if (filterJournalId.value) params.journal_id = filterJournalId.value
    const res = await getArticles(params)
    articles.value = res.articles
    total.value = res.articles.length // backend doesn't return total; will use current count for pagination display
  } finally {
    loading.value = false
  }
}

function loadPage(p: number) {
  page.value = p
  loadArticles()
}

watch(filterJournalId, () => { page.value = 1; loadArticles() })

onMounted(async () => {
  try { journals.value = (await getJournals()).journals } catch {}
  loadArticles()
})
</script>
