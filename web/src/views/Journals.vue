<template>
  <div>
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 4px; flex-wrap: wrap;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <n-h2 style="margin: 0;">期刊广场</n-h2>
        <n-tag v-if="!loading" size="small" :bordered="false">{{ total }} 源</n-tag>
      </div>
      <n-button size="small" :loading="loading && !!journals.length" :disabled="loading" @click="reload">刷新</n-button>
    </div>

    <n-space vertical style="margin-bottom: 16px;">
      <n-input
        v-model:value="q"
        clearable
        placeholder="搜索名称 / 描述 / slug"
        style="max-width: 360px;"
        :disabled="loading"
        @keyup.enter="reload"
        @clear="reload"
      >
        <template #suffix>
          <n-button text type="primary" :disabled="loading" @click="reload">搜索</n-button>
        </template>
      </n-input>
      <n-space align="center">
        <n-radio-group v-model:value="contentType" size="small" :disabled="loading" @update:value="reload">
          <n-radio-button value="">全部</n-radio-button>
          <n-radio-button value="journal">{{ contentTypeLabel('journal') }}</n-radio-button>
          <n-radio-button value="preprint">{{ contentTypeLabel('preprint') }}</n-radio-button>
        </n-radio-group>
        <n-radio-group v-model:value="sourceType" size="small" :disabled="loading" @update:value="reload">
          <n-radio-button value="">全部源</n-radio-button>
          <n-radio-button value="rss">{{ sourceTypeLabel('rss') }}</n-radio-button>
          <n-radio-button value="arxiv">{{ sourceTypeLabel('arxiv') }}</n-radio-button>
          <n-radio-button value="cnki">{{ sourceTypeLabel('cnki') }}</n-radio-button>
        </n-radio-group>
        <n-select
          v-model:value="sortBy"
          size="small"
          style="width: 140px;"
          :options="sortOptions"
          :disabled="loading"
        />
        <template v-if="categories.length">
          <n-tag v-if="casYear != null" size="small" :bordered="false" type="info">
            CAS {{ casYear }}
          </n-tag>
          <n-select
            v-model:value="major"
            clearable
            placeholder="CAS 大类"
            :options="majorOptions"
            style="width: 160px;"
            size="small"
            :disabled="loading"
            @update:value="onMajorChange"
          />
          <n-select
            v-model:value="minor"
            clearable
            placeholder="CAS 小类"
            :options="minorOptions"
            style="width: 160px;"
            size="small"
            :disabled="loading || !major"
            @update:value="reload"
          />
          <n-select
            v-model:value="zone"
            clearable
            placeholder="分区"
            :options="zoneOptions"
            style="width: 100px;"
            size="small"
            :disabled="loading"
            @update:value="reload"
          />
          <n-checkbox v-model:checked="topOnly" :disabled="loading" @update:checked="reload">仅 Top</n-checkbox>
        </template>
      </n-space>
    </n-space>

    <div v-if="loading" style="padding: 48px 0; text-align: center;"><n-spin /></div>
    <n-grid v-else-if="pageJournals.length" :cols="2" :y-gap="16" :x-gap="16">
      <n-gi v-for="j in pageJournals" :key="j.id">
        <n-card :title="j.name" hoverable @click="router.push(`/journals/${j.id}`)">
          <template #header-extra>
            <n-space size="small">
              <n-tag v-if="j.content_type === 'preprint'" type="info" size="small" :bordered="false">{{ contentTypeLabel(j.content_type) }}</n-tag>
              <n-tag :type="sourceTypeTagType(j.source_type)" size="small">
                {{ sourceTypeLabel(j.source_type) }}
              </n-tag>
              <n-tag
                v-if="j.health_status === 'paused'"
                type="error"
                size="small"
                :bordered="false"
                :title="j.last_error || '抓取已暂停'"
              >
                {{ healthStatusLabel(j.health_status) }}
              </n-tag>
            </n-space>
          </template>

          <div style="display: flex; gap: 16px; margin-bottom: 8px;">
            <n-statistic label="论文" :value="j.article_count" />
            <n-statistic label="更新" :value="j.last_article_date ? formatDate(j.last_article_date) : '暂无'" />
          </div>

          <p v-if="j.description" style="color: #555; font-size: 13px; line-height: 1.6; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            {{ j.description }}
          </p>

          <p style="color: #888; font-size: 12px; word-break: break-all;">
            <a
              :href="j.homepage_url || j.source_url"
              target="_blank" rel="noopener noreferrer"
              @click.stop
            >{{ shortUrl(j.homepage_url || j.source_url) }}</a>
          </p>

          <template #action>
            <template v-if="isLoggedIn">
              <n-button
                v-if="subscribedIds.has(j.id)"
                size="small"
                type="error"
                ghost
                :loading="busyIds.has(j.id)"
                :disabled="busyIds.has(j.id)"
                @click.stop="handleUnsubscribe(j)"
              >
                取消订阅
              </n-button>
              <n-button
                v-else
                size="small"
                type="primary"
                ghost
                :loading="busyIds.has(j.id)"
                :disabled="busyIds.has(j.id)"
                @click.stop="handleSubscribe(j)"
              >
                订阅
              </n-button>
            </template>
            <n-button
              v-else
              size="small"
              type="primary"
              ghost
              @click.stop="router.push({ path: '/login', query: { redirect: `/journals/${j.id}` } })"
            >
              登录后订阅
            </n-button>
            <n-button size="small" quaternary @click.stop="router.push(`/journals/${j.id}`)">
              浏览论文
            </n-button>
          </template>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!loading && total === 0" :description="emptyDescription">
      <template #extra>
        <n-button v-if="hasActiveFilters" @click="clearFilters">清除筛选</n-button>
        <template v-else>
          <n-button v-if="isLoggedIn" @click="router.push('/my/subscriptions')">添加 RSS 源</n-button>
          <n-button v-else @click="router.push('/login')">登录后添加源</n-button>
        </template>
      </template>
    </n-empty>
    <n-pagination
      v-if="pageCount > 1 && !loading"
      :page="page"
      :page-count="pageCount"
      :disabled="loading"
      style="margin-top: 16px;"
      @update:page="onPageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournals, type Journal } from '@/api/journals'
import { getCasCategories, type CasCategory } from '@/api/categories'
import {
  subscribeJournal,
  unsubscribeJournal,
  getSubscribedJournals,
} from '@/api/subscriptions'
import { useAuthStore } from '@/stores/auth'
import { shortUrl } from '@/utils/url'
import { sourceTypeLabel, sourceTypeTagType, contentTypeLabel, healthStatusLabel } from '@/utils/labels'
import { formatDate } from '@/utils/datetime'
import {
  NH2, NGrid, NGi, NCard, NTag, NEmpty, NButton, NStatistic, NInput, NSpace, NSpin,
  NRadioGroup, NRadioButton, NSelect, NCheckbox, NPagination, useMessage, useDialog,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)
const journals = ref<Journal[]>([])
const loading = ref(true)
const q = ref('')
const contentType = ref('')
const sourceType = ref('')
const sortBy = ref<'name' | 'articles' | 'updated'>('name')
const page = ref(1)
const pageSize = 24
const major = ref<string | null>(null)
const minor = ref<string | null>(null)
const zone = ref<string | null>(null)
const topOnly = ref(false)
/** Latest CAS year used for facet options and list filters. */
const casYear = ref<number | null>(null)
const categories = ref<CasCategory[]>([])
const subscribedIds = ref<Set<string>>(new Set())
const busyIds = ref<Set<string>>(new Set())
/** Drop stale plaza list responses when filters/page change mid-flight. */
let journalsLoadSeq = 0
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false
/** Skip sort watcher side effects while hydrating from the URL. */
let applyingFromQuery = false

const SORT_VALUES = new Set(['name', 'articles', 'updated'])

function pageFromQuery(): number {
  const raw = route.query.page
  const n = typeof raw === 'string' ? parseInt(raw, 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : 1
}

function applyFiltersFromQuery() {
  applyingFromQuery = true
  try {
    const qq = route.query
    q.value = typeof qq.q === 'string' ? qq.q : ''
    contentType.value = typeof qq.content_type === 'string' ? qq.content_type : ''
    sourceType.value = typeof qq.source_type === 'string' ? qq.source_type : ''
    const sort = typeof qq.sort === 'string' ? qq.sort : 'name'
    sortBy.value = (SORT_VALUES.has(sort) ? sort : 'name') as 'name' | 'articles' | 'updated'
    major.value = typeof qq.major === 'string' && qq.major ? qq.major : null
    minor.value = typeof qq.minor === 'string' && qq.minor ? qq.minor : null
    zone.value = typeof qq.zone === 'string' && qq.zone ? qq.zone : null
    topOnly.value = qq.top === 'true' || qq.top === '1'
    page.value = pageFromQuery()
  } finally {
    applyingFromQuery = false
  }
}

function syncFiltersToQuery() {
  const next: Record<string, string> = {}
  if (q.value.trim()) next.q = q.value.trim()
  if (contentType.value) next.content_type = contentType.value
  if (sourceType.value) next.source_type = sourceType.value
  if (sortBy.value && sortBy.value !== 'name') next.sort = sortBy.value
  if (major.value) next.major = major.value
  if (minor.value) next.minor = minor.value
  if (zone.value) next.zone = zone.value
  if (topOnly.value) next.top = 'true'
  if (page.value > 1) next.page = String(page.value)
  const cur = route.query
  const keys = ['q', 'content_type', 'source_type', 'sort', 'major', 'minor', 'zone', 'top', 'page'] as const
  const same = keys.every((k) => (cur[k] || undefined) === next[k])
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

const sortOptions = [
  { label: '按名称', value: 'name' },
  { label: '按论文数', value: 'articles' },
  { label: '按最近更新', value: 'updated' },
]

const total = ref(0)

const pageCount = computed(() => Math.ceil((total.value || 0) / pageSize) || 1)

/** Current page rows — server already sorted + sliced. */
const pageJournals = computed(() => journals.value)

const hasActiveFilters = computed(() =>
  Boolean(q.value.trim() || contentType.value || sourceType.value || major.value || minor.value || zone.value || topOnly.value),
)

const emptyDescription = computed(() =>
  hasActiveFilters.value ? '当前筛选下暂无期刊' : '暂无可浏览的期刊',
)

function onPageChange(p: number) {
  if (loading.value) return
  page.value = p
  window.scrollTo({ top: 0, behavior: 'smooth' })
  syncFiltersToQuery()
  fetchJournals()
}

function clearFilters() {
  if (loading.value) return
  q.value = ''
  contentType.value = ''
  sourceType.value = ''
  major.value = null
  minor.value = null
  zone.value = null
  topOnly.value = false
  page.value = 1
  syncFiltersToQuery()
  fetchJournals()
}

const majorOptions = computed(() => {
  const set = new Set(categories.value.map(c => c.major).filter(Boolean))
  return [...set].sort().map(m => ({ label: m, value: m }))
})

const minorOptions = computed(() => {
  if (!major.value) return []
  const set = new Set(
    categories.value.filter(c => c.major === major.value).map(c => c.minor).filter(Boolean),
  )
  return [...set].sort().map(m => ({ label: m, value: m }))
})

const zoneOptions = [
  { label: '1 区', value: '1' },
  { label: '2 区', value: '2' },
  { label: '3 区', value: '3' },
  { label: '4 区', value: '4' },
]

function onMajorChange() {
  if (loading.value) return
  minor.value = null
  page.value = 1
  syncFiltersToQuery()
  fetchJournals()
}

async function refreshSubscribed() {
  if (!auth.isLoggedIn) {
    subscribedIds.value = new Set()
    return
  }
  try {
    const res = await getSubscribedJournals()
    subscribedIds.value = new Set(res.journals.map((j) => j.id))
  } catch {
    // non-blocking
  }
}

async function handleSubscribe(j: Journal) {
  if (busyIds.value.has(j.id)) return
  busyIds.value = new Set([...busyIds.value, j.id])
  try {
    await subscribeJournal(j.id)
    subscribedIds.value = new Set([...subscribedIds.value, j.id])
    message.success(`已订阅「${j.name}」`)
  } catch (e: any) {
    message.error(e.message || '订阅失败')
  } finally {
    const next = new Set(busyIds.value)
    next.delete(j.id)
    busyIds.value = next
  }
}

function handleUnsubscribe(j: Journal) {
  if (busyIds.value.has(j.id)) return
  dialog.warning({
    title: '取消订阅',
    content: `确认取消订阅「${j.name}」？之后将不再收到该源的更新推送。`,
    positiveText: '取消订阅',
    negativeText: '返回',
    onPositiveClick: () => doUnsubscribe(j),
  })
}

async function doUnsubscribe(j: Journal) {
  if (busyIds.value.has(j.id)) return
  busyIds.value = new Set([...busyIds.value, j.id])
  try {
    await unsubscribeJournal(j.id)
    const next = new Set(subscribedIds.value)
    next.delete(j.id)
    subscribedIds.value = next
    message.success(`已取消订阅「${j.name}」`)
  } catch (e: any) {
    message.error(e.message || '取消失败')
  } finally {
    const next = new Set(busyIds.value)
    next.delete(j.id)
    busyIds.value = next
  }
}

async function reload() {
  if (loading.value) return
  page.value = 1
  syncFiltersToQuery()
  await fetchJournals()
}

async function fetchJournals() {
  const seq = ++journalsLoadSeq
  loading.value = true
  try {
    const hasCasFacet = Boolean(major.value || minor.value || zone.value || topOnly.value)
    const params: Record<string, string | number | undefined> = {
      q: q.value.trim() || undefined,
      content_type: contentType.value || undefined,
      source_type: sourceType.value || undefined,
      major: major.value || undefined,
      minor: minor.value || undefined,
      zone: zone.value || undefined,
      top: topOnly.value ? 'true' : undefined,
      // Align CAS journal filter with the year the facet options came from.
      year: hasCasFacet && casYear.value != null ? casYear.value : undefined,
      sort: sortBy.value,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    }
    const res = await getJournals(params)
    if (seq !== journalsLoadSeq) return
    journals.value = res.journals
    total.value = typeof res.total === 'number' ? res.total : res.journals.length
  } catch (e: any) {
    if (seq !== journalsLoadSeq) return
    message.error(e.message || '加载失败')
  } finally {
    if (seq === journalsLoadSeq) loading.value = false
  }
}

watch(sortBy, () => {
  if (applyingFromQuery) return
  page.value = 1
  syncFiltersToQuery()
  fetchJournals()
})

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
    syncFiltersToQuery()
    fetchJournals()
  }
})

watch(
  () => [
    route.query.q,
    route.query.content_type,
    route.query.source_type,
    route.query.sort,
    route.query.major,
    route.query.minor,
    route.query.zone,
    route.query.top,
    route.query.page,
  ],
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyFiltersFromQuery()
    fetchJournals()
  },
)

onMounted(async () => {
  applyFiltersFromQuery()
  try {
    // Prefer latest CAS year so major/minor options aren't a mix of outdated labels.
    const cas = await getCasCategories()
    const years = cas.years?.length
      ? cas.years
      : [...new Set(cas.categories.map((c) => c.year))].sort((a, b) => b - a)
    const latest = years[0]
    if (latest != null) {
      casYear.value = latest
      const scoped = await getCasCategories({ year: latest })
      categories.value = scoped.categories
    } else {
      casYear.value = null
      categories.value = cas.categories
    }
  } catch {
    // CAS optional
  }
  await Promise.all([fetchJournals(), refreshSubscribed()])
})
</script>
