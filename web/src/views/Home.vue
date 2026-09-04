<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
      <n-h2 style="margin: 0;">公开广场</n-h2>
      <n-button size="small" :loading="loading && !!articles.length" @click="loadArticles">刷新</n-button>
    </div>
    <n-alert v-if="auth.isLoggedIn" type="info" style="margin-bottom: 16px;" :bordered="false">
      已登录用户可在
      <n-button text type="primary" @click="router.push('/my')">我的更新</n-button>
      查看订阅命中与阅读状态。
    </n-alert>
    <n-alert v-else type="default" style="margin-bottom: 16px;" :bordered="false">
      浏览公开论文与期刊；
      <n-button text type="primary" @click="router.push('/login')">登录</n-button>
      后可订阅、标记已读并接收推送。
    </n-alert>
    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap;">
      <n-radio-group v-model:value="filterContentType" size="small" @update:value="onContentTypeChange">
        <n-radio-button value="">全部</n-radio-button>
        <n-radio-button value="journal">{{ contentTypeLabel('journal') }}</n-radio-button>
        <n-radio-button value="preprint">{{ contentTypeLabel('preprint') }}</n-radio-button>
      </n-radio-group>
      <n-select
        v-if="journals.length"
        v-model:value="filterJournalId"
        :options="journalOptions"
        placeholder="筛选期刊"
        clearable
        filterable
        style="max-width: 300px;"
      />
      <n-tag v-if="!loading" :bordered="false">{{ total }} 篇</n-tag>
    </div>

    <div v-if="loading"><n-spin /></div>
    <n-empty v-else-if="!articles.length" :description="emptyDescription">
      <template #extra>
        <n-button v-if="filterJournalId || filterContentType" @click="clearFilters">清除筛选</n-button>
        <n-button v-else @click="router.push('/journals')">浏览期刊</n-button>
      </template>
    </n-empty>

    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing>
          <template #header>
            <router-link :to="`/articles/${a.id}`" style="text-decoration: none; color: inherit;">
              {{ a.title }}
            </router-link>
          </template>
          <template #description>
            <div style="margin-bottom: 6px;">
              <router-link
                v-if="a.journal_id && a.journal_name"
                :to="`/journals/${a.journal_id}`"
                style="text-decoration: none; margin-right: 6px;"
              >
                <n-tag size="tiny" :bordered="false">{{ a.journal_name }}</n-tag>
              </router-link>
              <n-tag v-else-if="a.journal_name" size="tiny" :bordered="false" style="margin-right: 6px;">
                {{ a.journal_name }}
              </n-tag>
              <n-tag v-if="a.content_type === 'preprint'" type="info" size="tiny" :bordered="false" style="margin-right: 6px;">
                {{ contentTypeLabel(a.content_type) }}
              </n-tag>
              <n-tag :type="a.journal_source_type === 'arxiv' ? 'info' : 'success'" size="tiny" :bordered="false">
                {{ sourceTypeLabel(a.journal_source_type) }}
              </n-tag>
            </div>
            <span style="color: #888; font-size: 13px;">作者：{{ formatAuthors(a.authors) }}</span>
            <br>
            <span style="color: #aaa; font-size: 12px;">{{ formatDate(a.publish_date) }}</span>
          </template>
          <template #action>
            <div style="display: flex; gap: 4px;">
              <n-button size="tiny" quaternary tag="a" :href="`/articles/${a.id}`" @click.prevent="router.push(`/articles/${a.id}`)">详情</n-button>
              <n-button v-if="a.doi" size="tiny" quaternary tag="a" :href="doiUrl(a.doi)" target="_blank" rel="noopener noreferrer">DOI</n-button>
              <n-button v-if="a.url" size="tiny" quaternary tag="a" :href="a.url" target="_blank" rel="noopener noreferrer">原文</n-button>
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
import { useAuthStore } from '@/stores/auth'
import { truncateAbstract } from '@/utils/abstract'
import { formatDate } from '@/utils/datetime'
import { doiUrl } from '@/utils/url'
import { formatAuthors, sourceTypeLabel, contentTypeLabel } from '@/utils/labels'
import {
  NH2, NSelect, NSpin, NEmpty, NList, NListItem, NThing, NPagination, NTag, NButton, NAlert,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const articles = ref<Article[]>([])
const journals = ref<Journal[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const limit = 20
const filterJournalId = ref<string | null>(null)
const filterContentType = ref('')

const pageCount = computed(() => Math.ceil(total.value / limit) || 1)

const journalOptions = computed(() =>
  journals.value.map(j => ({ label: `${j.name} (${j.article_count}篇)`, value: j.id }))
)

const emptyDescription = computed(() => {
  if (filterJournalId.value || filterContentType.value) return '当前筛选下暂无文章'
  return '暂无文章'
})

function clearFilters() {
  filterJournalId.value = null
  filterContentType.value = ''
  page.value = 1
  loadArticles()
}


function onContentTypeChange() {
  page.value = 1
  loadArticles()
}

async function loadArticles() {
  loading.value = true
  try {
    const params: Record<string, string> = {
      limit: String(limit),
      offset: String((page.value - 1) * limit),
    }
    if (filterJournalId.value) params.journal_id = filterJournalId.value
    if (filterContentType.value) params.content_type = filterContentType.value
    const res = await getArticles(params)
    articles.value = res.articles
    // Prefer server total; fall back to page length only when absent.
    total.value = typeof res.total === 'number' ? res.total : res.articles.length
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function loadPage(p: number) {
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  loadArticles()
}

watch(filterJournalId, () => { page.value = 1; loadArticles() })

onMounted(async () => {
  try {
    // Name-sorted page is enough for the filter dropdown; avoid full catalog pull.
    journals.value = (await getJournals({ sort: 'name', limit: 200, offset: 0 })).journals
  } catch {
    // journal filter is optional; articles load still proceeds
  }
  loadArticles()
})
</script>
