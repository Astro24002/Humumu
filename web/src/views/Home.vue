<template>
  <div>
    <n-h2>最新论文</n-h2>
    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px;">
      <n-select v-if="journals.length" v-model:value="filterJournalId" :options="journalOptions"
        placeholder="筛选期刊" clearable style="max-width: 300px;" />
      <n-tag v-if="!loading" :bordered="false">{{ articles.length }} 篇</n-tag>
    </div>

    <div v-if="loading"><n-spin /></div>
    <n-empty v-else-if="!articles.length" description="暂无文章" />

    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing :title="a.title">
          <template #description>
            <div style="margin-bottom: 6px;">
              <n-tag v-if="a.journal_name" size="tiny" :bordered="false" style="margin-right: 6px;">
                {{ a.journal_name }}
              </n-tag>
              <n-tag :type="a.journal_source_type === 'arxiv' ? 'info' : 'success'" size="tiny" :bordered="false">
                {{ a.journal_source_type }}
              </n-tag>
            </div>
            <span style="color: #888; font-size: 13px;">作者：{{ a.authors?.slice(0, 3).join(', ') }}{{ a.authors?.length > 3 ? ' 等' : '' }}</span>
            <br>
            <span style="color: #aaa; font-size: 12px;">{{ a.publish_date || '' }}</span>
          </template>
          <template #action>
            <div style="display: flex; gap: 4px;">
              <n-button size="tiny" quaternary tag="a" :href="`/articles/${a.id}`" @click.prevent="router.push(`/articles/${a.id}`)">详情</n-button>
              <n-button v-if="a.doi" size="tiny" quaternary tag="a" :href="doiUrl(a.doi)" target="_blank">DOI</n-button>
            </div>
          </template>
          <template #footer>
            <p v-if="a.abstract" style="color: #999; font-size: 12px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
              {{ truncateAbstract(a.abstract) }}
            </p>
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
import { useRouter } from 'vue-router'
import { getArticles, type Article } from '@/api/articles'
import { getJournals, type Journal } from '@/api/journals'
import { NH2, NSelect, NSpin, NEmpty, NList, NListItem, NThing, NPagination, NTag, NButton } from 'naive-ui'

const router = useRouter()
const articles = ref<Article[]>([])
const journals = ref<Journal[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const limit = 20
const filterJournalId = ref<string | null>(null)

const pageCount = computed(() => Math.ceil(total.value / limit) || 1)

const journalOptions = computed(() =>
  journals.value.map(j => ({ label: `${j.name} (${j.article_count}篇)`, value: j.id }))
)

function doiUrl(doi: string): string {
  if (doi.startsWith('http')) return doi
  return `https://doi.org/${doi}`
}

function truncateAbstract(text: string): string {
  // Remove arXiv prefix "arXiv:... Announce Type: ... \nAbstract:"
  const cleaned = text.replace(/^arXiv:\S+ Announce Type: \S+\s*\n\s*Abstract:\s*/i, '')
  return cleaned.length > 200 ? cleaned.slice(0, 200) + '...' : cleaned
}

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
    total.value = res.articles.length
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
