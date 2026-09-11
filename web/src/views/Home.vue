<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
      <n-h2 style="margin: 0;">公开广场</n-h2>
      <n-button size="small" :loading="loading && !!articles.length" :disabled="loading" @click="reload">刷新</n-button>
    </div>
    <n-alert v-if="auth.isLoggedIn" type="info" style="margin-bottom: 16px;" :bordered="false">
      已登录用户可在
      <n-button text type="primary" @click="router.push('/my')">我的更新</n-button>
      查看订阅命中与阅读状态。
    </n-alert>
    <n-alert v-else type="default" style="margin-bottom: 16px;" :bordered="false">
      浏览公开论文与期刊。请先
      <n-button text type="primary" @click="router.push('/register')">用邮箱注册</n-button>
      或
      <n-button text type="primary" @click="router.push('/login')">登录</n-button>
      ，再订阅并接收邮件推送；微信小程序可用同一邮箱绑定微信。
    </n-alert>
    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap;">
      <n-radio-group v-model:value="filterContentType" size="small" :disabled="loading" @update:value="onFilterChange">
        <n-radio-button value="">全部</n-radio-button>
        <n-radio-button value="journal">{{ contentTypeLabel('journal') }}</n-radio-button>
        <n-radio-button value="preprint">{{ contentTypeLabel('preprint') }}</n-radio-button>
      </n-radio-group>
      <n-radio-group v-model:value="filterSourceType" size="small" :disabled="loading" @update:value="onFilterChange">
        <n-radio-button value="">全部源</n-radio-button>
        <n-radio-button value="rss">{{ sourceTypeLabel('rss') }}</n-radio-button>
        <n-radio-button value="arxiv">{{ sourceTypeLabel('arxiv') }}</n-radio-button>
        <n-radio-button value="cnki">{{ sourceTypeLabel('cnki') }}</n-radio-button>
      </n-radio-group>
      <n-select
        v-model:value="filterJournalId"
        :options="journalOptions"
        placeholder="筛选期刊"
        clearable
        filterable
        remote
        :disabled="loading"
        :loading="journalSearchLoading"
        :reset-menu-on-options-change="false"
        style="max-width: 300px;"
        @search="onJournalSearch"
        @focus="onJournalFocus"
      />
      <n-tag v-if="!loading" :bordered="false">{{ total }} 篇</n-tag>
    </div>

    <div v-if="loading"><n-spin /></div>
    <n-empty v-else-if="!articles.length" :description="emptyDescription">
      <template #extra>
        <n-button v-if="filterJournalId || filterContentType || filterSourceType" :disabled="loading" @click="clearFilters">清除筛选</n-button>
        <n-button v-else :disabled="loading" @click="router.push('/journals')">浏览期刊</n-button>
      </template>
    </n-empty>

    <n-list v-else :style="loading ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing>
          <template #header>
                        <router-link
              :to="`/articles/${a.id}`"
              :style="homeTitleStyle(a.id)"
              @click="(e: MouseEvent) => { if (loading || originalClickBusy.has(a.id)) e.preventDefault() }"
            >
              {{ a.title }}
            </router-link>
          </template>
          <template #description>
            <div style="margin-bottom: 6px;">
              <router-link
                v-if="a.journal_id && a.journal_name"
                :to="`/journals/${a.journal_id}`"
                :style="homeJournalNavStyle(a.id)"
                @click="(e: MouseEvent) => { if (loading || originalClickBusy.has(a.id)) e.preventDefault() }"
              >
                <n-tag size="tiny" :bordered="false">{{ a.journal_name }}</n-tag>
              </router-link>
              <n-tag v-else-if="a.journal_name" size="tiny" :bordered="false" style="margin-right: 6px;">
                {{ a.journal_name }}
              </n-tag>
              <n-tag v-if="a.content_type === 'preprint'" type="info" size="tiny" :bordered="false" style="margin-right: 6px;">
                {{ contentTypeLabel(a.content_type) }}
              </n-tag>
              <n-tag
                v-if="a.journal_source_type"
                :type="sourceTypeTagType(a.journal_source_type)"
                size="tiny"
                :bordered="false"
              >
                {{ sourceTypeLabel(a.journal_source_type) }}
              </n-tag>
            </div>
            <template v-if="a.authors?.length">
              <span style="color: #888; font-size: 13px;">作者：{{ formatAuthors(a.authors) }}</span>
              <br>
            </template>
            <span style="color: #aaa; font-size: 12px;">{{ formatDate(a.publish_date) }}</span>
          </template>
          <template #action>
            <div style="display: flex; gap: 4px;">
              <n-button
                size="tiny"
                quaternary
                tag="a"
                :href="`/articles/${a.id}`"
                :disabled="loading || originalClickBusy.has(a.id)"
                @click.prevent="!(loading || originalClickBusy.has(a.id)) && router.push(`/articles/${a.id}`)"
              >详情</n-button>
              <n-button
                v-if="a.doi"
                size="tiny"
                quaternary
                tag="a"
                :href="doiUrl(a.doi)"
                target="_blank"
                rel="noopener noreferrer"
                :disabled="loading || originalClickBusy.has(a.id)"
                @click="onOriginalClick(a.id)"
              >DOI</n-button>
              <n-button
                v-if="a.url"
                size="tiny"
                quaternary
                tag="a"
                :href="a.url"
                target="_blank"
                rel="noopener noreferrer"
                :disabled="loading || originalClickBusy.has(a.id)"
                @click="onOriginalClick(a.id)"
              >原文</n-button>
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

    <n-pagination
      v-if="pageCount > 1 && !loading"
      :page="page"
      :page-count="pageCount"
      :disabled="loading"
      @update:page="loadPage"
      style="margin-top: 16px;"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticles, type Article } from '@/api/articles'
import { getJournal, getJournals, type Journal } from '@/api/journals'
import { recordOriginalClick } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { truncateAbstract } from '@/utils/abstract'
import { formatDate } from '@/utils/datetime'
import { doiUrl } from '@/utils/url'
import { formatAuthors, sourceTypeLabel, sourceTypeTagType, contentTypeLabel } from '@/utils/labels'
import {
  NH2, NSelect, NSpin, NEmpty, NList, NListItem, NThing, NPagination, NTag, NButton, NAlert,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const articles = ref<Article[]>([])
const journals = ref<Journal[]>([])
const journalSearchLoading = ref(false)
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const limit = 20
const filterJournalId = ref<string | null>(null)
const filterContentType = ref('')
const filterSourceType = ref('')
let journalSearchSeq = 0
/** Drop stale plaza list responses when filters/page change mid-flight. */
let articlesLoadSeq = 0
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false
/** Skip journal-id watcher side effects while hydrating from the URL. */
let applyingFromQuery = false
const originalClickBusy = ref(new Set<string>())

function homeTitleStyle(articleId: string) {
  const base: Record<string, string> = { textDecoration: 'none', color: 'inherit' }
  if (loading.value || originalClickBusy.value.has(articleId)) {
    base.opacity = '0.55'
    base.pointerEvents = 'none'
  }
  return base
}

function homeJournalNavStyle(articleId: string) {
  const base: Record<string, string> = { textDecoration: 'none', marginRight: '6px' }
  if (loading.value || originalClickBusy.value.has(articleId)) {
    base.opacity = '0.55'
    base.pointerEvents = 'none'
  }
  return base
}
/** Session-local: list cards lack status payload; skip re-mark after first success. */
async function onOriginalClick(articleId: string) {
  if (!auth.isLoggedIn || !articleId || originalClickBusy.value.has(articleId)) return
  originalClickBusy.value = new Set([...originalClickBusy.value, articleId])
  try {
    // Server marks read + original_clicked_at; skip a second status PUT.
    await recordOriginalClick(articleId)
  } catch {
    // non-blocking
  } finally {
    const next = new Set(originalClickBusy.value)
    next.delete(articleId)
    originalClickBusy.value = next
  }
}

function pageFromQuery(): number {
  const raw = route.query.page
  const n = typeof raw === 'string' ? parseInt(raw, 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : 1
}

function applyFiltersFromQuery() {
  applyingFromQuery = true
  try {
    const q = route.query
    filterContentType.value = typeof q.content_type === 'string' ? q.content_type : ''
    filterSourceType.value = typeof q.source_type === 'string' ? q.source_type : ''
    filterJournalId.value = typeof q.journal_id === 'string' && q.journal_id ? q.journal_id : null
    page.value = pageFromQuery()
  } finally {
    applyingFromQuery = false
  }
}

function syncFiltersToQuery() {
  const next: Record<string, string> = {}
  if (filterContentType.value) next.content_type = filterContentType.value
  if (filterSourceType.value) next.source_type = filterSourceType.value
  if (filterJournalId.value) next.journal_id = filterJournalId.value
  if (page.value > 1) next.page = String(page.value)
  const cur = route.query
  const same =
    (cur.content_type || undefined) === next.content_type
    && (cur.source_type || undefined) === next.source_type
    && (cur.journal_id || undefined) === next.journal_id
    && (cur.page || undefined) === next.page
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

const pageCount = computed(() => Math.ceil(total.value / limit) || 1)

const journalOptions = computed(() =>
  journals.value.map(j => ({ label: `${j.name} (${j.article_count ?? 0}篇)`, value: j.id }))
)

async function fetchJournalOptions(q = '') {
  const seq = ++journalSearchSeq
  journalSearchLoading.value = true
  try {
    const res = await getJournals({
      q: q.trim() || undefined,
      sort: 'name',
      limit: 50,
      offset: 0,
    })
    if (seq !== journalSearchSeq) return
    const keepId = filterJournalId.value
    const keep = keepId ? journals.value.find(j => j.id === keepId) : undefined
    journals.value = res.journals
    if (keep && !journals.value.some(j => j.id === keep.id)) {
      journals.value = [keep, ...journals.value]
    }
  } catch {
    // filter is optional
  } finally {
    if (seq === journalSearchSeq) journalSearchLoading.value = false
  }
}

function onJournalSearch(q: string) {
  if (loading.value) return
  fetchJournalOptions(q)
}

function onJournalFocus() {
  if (loading.value) return
  if (!journals.value.length) fetchJournalOptions('')
}

const emptyDescription = computed(() => {
  if (filterJournalId.value || filterContentType.value || filterSourceType.value) return '当前筛选下暂无文章'
  return '暂无文章'
})

function clearFilters() {
  if (loading.value) return
  filterJournalId.value = null
  filterContentType.value = ''
  filterSourceType.value = ''
  page.value = 1
  syncFiltersToQuery()
  loadArticles()
}

function onFilterChange() {
  if (loading.value) return
  page.value = 1
  syncFiltersToQuery()
  loadArticles()
}

function reload() {
  if (loading.value) return
  loadArticles()
}

async function loadArticles() {
  const seq = ++articlesLoadSeq
  loading.value = true
  try {
    const params: Record<string, string> = {
      limit: String(limit),
      offset: String((page.value - 1) * limit),
    }
    if (filterJournalId.value) params.journal_id = filterJournalId.value
    if (filterContentType.value) params.content_type = filterContentType.value
    if (filterSourceType.value) params.source_type = filterSourceType.value
    const res = await getArticles(params)
    if (seq !== articlesLoadSeq) return
    articles.value = res.articles
    // Prefer server total; fall back to page length only when absent.
    total.value = typeof res.total === 'number' ? res.total : res.articles.length
  } catch (e: any) {
    if (seq !== articlesLoadSeq) return
    message.error(e?.message || '加载失败')
  } finally {
    if (seq === articlesLoadSeq) loading.value = false
  }
}

function loadPage(p: number) {
  if (loading.value) return
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  syncFiltersToQuery()
  loadArticles()
}

watch(filterJournalId, () => {
  if (applyingFromQuery || loading.value) return
  page.value = 1
  syncFiltersToQuery()
  loadArticles()
})

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
    syncFiltersToQuery()
    loadArticles()
  }
})

watch(
  () => [route.query.content_type, route.query.source_type, route.query.journal_id, route.query.page],
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyFiltersFromQuery()
    loadArticles()
  },
)

onUnmounted(() => { articlesLoadSeq++ })
onMounted(async () => {
  applyFiltersFromQuery()
  // Remote-search dropdown; seed first page so the control isn't empty on open.
  await fetchJournalOptions('')
  // Deep-linked journal_id may not be in the first search page — hydrate its label.
  const keepId = filterJournalId.value
  if (keepId && !journals.value.some((j) => j.id === keepId)) {
    try {
      const j = await getJournal(keepId)
      journals.value = [j, ...journals.value]
    } catch {
      // leave bare id if private / missing
    }
  }
  loadArticles()
})
</script>
