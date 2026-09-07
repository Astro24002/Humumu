<template>
  <n-button quaternary @click="goBack" style="margin-bottom: 16px;">← 返回</n-button>

  <div v-if="loading"><n-spin /></div>
  <n-result v-else-if="loadError" status="404" :title="loadError" description="可能是私有源或已删除">
    <template #footer>
      <n-button @click="router.push('/journals')">期刊广场</n-button>
      <n-button type="primary" style="margin-left: 8px;" @click="router.push('/my/subscriptions')">我的订阅</n-button>
    </template>
  </n-result>
  <template v-else-if="journal">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
      <n-h2 style="margin-bottom: 0;">{{ journal.name }}</n-h2>
      <n-tag v-if="journal.content_type === 'preprint'" type="info" size="small" :bordered="false">{{ contentTypeLabel(journal.content_type) }}</n-tag>
      <n-tag :type="sourceTypeTagType(journal.source_type)" size="small">
        {{ sourceTypeLabel(journal.source_type) }}
      </n-tag>
      <n-tag
        v-if="journal.directory_status && journal.directory_status !== 'public'"
        :type="dirStatusType(journal.directory_status)"
        size="small"
        :bordered="false"
      >
        {{ dirStatusLabel(journal.directory_status) }}
      </n-tag>
      <n-tag
        v-if="journal.health_status === 'paused'"
        type="error"
        size="small"
        :bordered="false"
        :title="journal.last_error || '抓取已暂停'"
      >
        {{ healthStatusLabel(journal.health_status) }}
      </n-tag>
    </div>

    <n-descriptions label-placement="left" :column="3" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="论文总数">
        <n-number-animation :from="0" :to="journal.article_count ?? 0" />
      </n-descriptions-item>
      <n-descriptions-item label="数据源">
        <a
          :href="journal.source_url"
          target="_blank"
          rel="noopener noreferrer"
          :style="articlesBusy ? { wordBreak: 'break-all', opacity: 0.55, pointerEvents: 'none' } : { wordBreak: 'break-all' }"
          @click="(e: MouseEvent) => { if (articlesBusy) e.preventDefault() }"
        >{{ shortUrl(journal.source_url) }}</a>
      </n-descriptions-item>
      <n-descriptions-item label="最新论文">
        {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}
      </n-descriptions-item>
      <n-descriptions-item v-if="journal.homepage_url" label="主页">
        <a
          :href="journal.homepage_url"
          target="_blank"
          rel="noopener noreferrer"
          :style="articlesBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined"
          @click="(e: MouseEvent) => { if (articlesBusy) e.preventDefault() }"
        >{{ shortUrl(journal.homepage_url) }}</a>
      </n-descriptions-item>
    </n-descriptions>

    <n-card v-if="journal.description" size="small" style="margin-bottom: 16px;">
      <template #header><strong>📖 期刊介绍</strong></template>
      {{ journal.description }}
    </n-card>

    <div style="margin-bottom: 16px;">
      <template v-if="isLoggedIn">
        <n-button
          v-if="isSubscribed"
          type="error"
          ghost
          :loading="subBusy"
          :disabled="articlesBusy"
          @click="handleUnsubscribe"
        >
          取消订阅
        </n-button>
        <n-button
          v-else
          type="primary"
          ghost
          :loading="subBusy"
          :disabled="articlesBusy"
          @click="handleSubscribe"
        >
          订阅此期刊
        </n-button>
      </template>
      <n-button
        v-else
        type="primary"
        ghost
        :disabled="articlesBusy"
        @click="router.push({ path: '/login', query: { redirect: route.fullPath } })"
      >
        登录后订阅
      </n-button>
    </div>

    <n-divider />

    <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; flex-wrap: wrap;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <n-h3 style="margin: 0;">论文列表</n-h3>
        <n-tag v-if="!articlesLoading && articlesTotal > 0" size="small" :bordered="false">{{ articlesTotal }} 篇</n-tag>
      </div>
      <n-button
        size="small"
        :loading="articlesLoading && !!articles.length"
        :disabled="articlesBusy"
        @click="reloadArticles"
      >刷新</n-button>
    </div>
    <div v-if="articlesLoading && !articles.length" style="padding: 24px 0; text-align: center;"><n-spin /></div>
    <n-empty
      v-else-if="!articles.length"
      :description="journal.health_status === 'paused' ? '暂无文章（抓取已暂停）' : '暂无文章'"
    >
      <template #extra>
        <n-button :disabled="articlesBusy" @click="router.push('/journals')">返回期刊广场</n-button>
      </template>
    </n-empty>
    <n-list v-else :style="articlesBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing>
          <template #header>
            <router-link
              :to="`/articles/${a.id}`"
              :style="articlesBusy ? { textDecoration: 'none', color: 'inherit', opacity: '0.55', pointerEvents: 'none' } : { textDecoration: 'none', color: 'inherit' }"
              @click="(e: MouseEvent) => { if (articlesBusy) e.preventDefault() }"
            >
              {{ a.title }}
            </router-link>
          </template>
          <template #description>
            <n-tag v-if="a.content_type === 'preprint'" type="info" size="tiny" :bordered="false" style="margin-right: 6px;">
              {{ contentTypeLabel(a.content_type) }}
            </n-tag>
            <template v-if="a.authors?.length">
              <span style="color: #888; font-size: 13px;">作者：{{ formatAuthors(a.authors) }}</span>
              <br>
            </template>
            <span style="color: #aaa; font-size: 12px;">{{ formatDate(a.publish_date) }}</span>
            <p
              v-if="a.abstract"
              style="color: #999; font-size: 12px; line-height: 1.6; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
            >
              {{ truncateAbstract(a.abstract) }}
            </p>
          </template>
          <template #footer>
            <n-space size="small">
              <router-link
                :to="`/articles/${a.id}`"
                :style="articlesBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined"
                @click="(e: MouseEvent) => { if (articlesBusy) e.preventDefault() }"
              >查看详情</router-link>
              <n-button
                v-if="a.doi"
                size="tiny"
                quaternary
                tag="a"
                :href="doiUrl(a.doi)"
                target="_blank"
                rel="noopener noreferrer"
                :disabled="articlesBusy || originalClickBusy.has(a.id)"
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
                :disabled="articlesBusy || originalClickBusy.has(a.id)"
                @click="onOriginalClick(a.id)"
              >原文</n-button>
            </n-space>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>
    <n-pagination
      v-if="articlesPageCount > 1 && !articlesLoading"
      :page="articlesPage"
      :page-count="articlesPageCount"
      :disabled="articlesBusy"
      style="margin-top: 16px;"
      @update:page="(p: number) => loadArticlesPage(p)"
    />
  </template>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import {
  subscribeJournal,
  unsubscribeJournal,
  getSubscribedJournals,
} from '@/api/subscriptions'
import { recordOriginalClick } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { truncateAbstract } from '@/utils/abstract'
import { shortUrl, doiUrl } from '@/utils/url'
import { formatDate } from '@/utils/datetime'
import { formatAuthors, dirStatusLabel, dirStatusType, sourceTypeLabel, sourceTypeTagType, contentTypeLabel, healthStatusLabel } from '@/utils/labels'
import {
  NH2, NH3, NButton, NCard, NTag, NDivider, NSpin, NEmpty, NResult,
  NList, NListItem, NThing, NDescriptions, NDescriptionsItem,
  NNumberAnimation, NPagination, NSpace, useMessage, useDialog,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/journals')
}
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)
const loadError = ref('')
const articlesLoading = ref(false)
const articlesTotal = ref(0)
const articlesPage = ref(1)
const articlesLimit = 20
const articlesPageCount = computed(() => Math.ceil(articlesTotal.value / articlesLimit) || 1)
const isSubscribed = ref(false)
const subBusy = ref(false)
/** Paper list controls locked while articles load or subscribe mutates. */
const articlesBusy = computed(() => articlesLoading.value || subBusy.value)
/** Drop stale article-list responses when route id / page changes mid-flight. */
let articlesLoadSeq = 0
const originalClickBusy = ref(new Set<string>())
/** Session-local: paper list cards lack status payload; skip re-mark after first success. */
async function onOriginalClick(articleId: string) {
  if (!isLoggedIn.value || !articleId || originalClickBusy.value.has(articleId) || articlesBusy.value) return
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
/** Drop stale journal detail responses when route id changes mid-flight. */
let journalLoadSeq = 0
/** Skip one route→state write when we just pushed page ourselves. */
let suppressPageApply = false
/** Skip page watcher side effects while hydrating journal / URL. */
let applyingPageFromQuery = false

function pageFromQuery(): number {
  const raw = route.query.page
  const n = typeof raw === 'string' ? parseInt(raw, 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : 1
}

function syncPageToQuery() {
  const next = { ...route.query } as Record<string, string | string[] | undefined>
  if (articlesPage.value > 1) next.page = String(articlesPage.value)
  else delete next.page
  const curPage = typeof route.query.page === 'string' ? route.query.page : undefined
  const wantPage = articlesPage.value > 1 ? String(articlesPage.value) : undefined
  if (curPage === wantPage) return
  suppressPageApply = true
  router.replace({ query: next })
}

watch(articlesPageCount, (n) => {
  if (articlesPage.value > n) loadArticlesPage(n)
})

async function handleSubscribe() {
  if (!journal.value || subBusy.value || articlesLoading.value) return
  subBusy.value = true
  try {
    await subscribeJournal(journal.value.id)
    isSubscribed.value = true
    message.success(`已订阅「${journal.value.name}」`)
  } catch (e: any) {
    message.error(e?.message || e?.response?.data?.error || '订阅失败')
  } finally {
    subBusy.value = false
  }
}

function handleUnsubscribe() {
  if (!journal.value || subBusy.value || articlesLoading.value) return
  const name = journal.value.name
  dialog.warning({
    title: '取消订阅',
    content: `确认取消订阅「${name}」？之后将不再收到该源的更新推送。`,
    positiveText: '取消订阅',
    negativeText: '返回',
    onPositiveClick: () => doUnsubscribe(),
  })
}

async function doUnsubscribe() {
  if (!journal.value || subBusy.value || articlesLoading.value) return
  subBusy.value = true
  try {
    await unsubscribeJournal(journal.value.id)
    isSubscribed.value = false
    message.success('已取消订阅')
  } catch (e: any) {
    message.error(e?.message || '取消失败')
  } finally {
    subBusy.value = false
  }
}

function reloadArticles() {
  if (articlesBusy.value) return
  loadArticlesPage(articlesPage.value)
}

async function loadArticlesPage(p: number, opts: { fromQuery?: boolean } = {}) {
  if ((articlesLoading.value || subBusy.value) && !opts.fromQuery) return
  const id = route.params.id as string
  const seq = ++articlesLoadSeq
  articlesPage.value = p
  if (!opts.fromQuery) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    syncPageToQuery()
  }
  articlesLoading.value = true
  try {
    const ar = await getArticles({
      journal_id: id,
      limit: String(articlesLimit),
      offset: String((p - 1) * articlesLimit),
    })
    if (seq !== articlesLoadSeq) return
    articles.value = ar.articles
    articlesTotal.value = ar.total ?? ar.articles.length
  } catch (e: any) {
    if (seq !== articlesLoadSeq) return
    message.error(e?.message || '加载论文列表失败')
  } finally {
    if (seq === articlesLoadSeq) articlesLoading.value = false
  }
}

async function loadJournal(id: string) {
  const seq = ++journalLoadSeq
  // Bump articles seq so in-flight list loads from a prior journal are dropped.
  articlesLoadSeq++
  loading.value = true
  loadError.value = ''
  journal.value = null
  articles.value = []
  articlesTotal.value = 0
  applyingPageFromQuery = true
  const startPage = pageFromQuery()
  articlesPage.value = startPage
  applyingPageFromQuery = false
  isSubscribed.value = false
  try {
    const [jr, , subRes] = await Promise.all([
      getJournal(id),
      loadArticlesPage(startPage, { fromQuery: true }),
      auth.isLoggedIn ? getSubscribedJournals().catch(() => null) : Promise.resolve(null),
    ])
    if (seq !== journalLoadSeq) return
    journal.value = jr
    // Prefer journal.article_count until the paged list reports total.
    if (typeof jr?.article_count === 'number' && jr.article_count > 0 && !articlesTotal.value) {
      articlesTotal.value = jr.article_count
    }
    if (jr?.name) document.title = `${jr.name} · Humumu`
    if (subRes) {
      isSubscribed.value = subRes.journals.some((j) => j.id === id)
    }
  } catch (e: any) {
    if (seq !== journalLoadSeq) return
    loadError.value = e?.message || '期刊不存在或无权查看'
  } finally {
    if (seq === journalLoadSeq) loading.value = false
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string' && id) loadJournal(id)
  },
)

watch(
  () => route.query.page,
  () => {
    if (suppressPageApply) {
      suppressPageApply = false
      return
    }
    if (applyingPageFromQuery) return
    if (loading.value || !journal.value) return
    const next = pageFromQuery()
    if (next === articlesPage.value) return
    loadArticlesPage(next, { fromQuery: true })
  },
)

onUnmounted(() => { journalLoadSeq++; articlesLoadSeq++ })
onMounted(() => {
  const id = route.params.id as string
  if (id) loadJournal(id)
})
</script>
