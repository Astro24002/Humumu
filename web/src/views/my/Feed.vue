<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
    <div style="display: flex; align-items: center; gap: 12px;">
      <n-h2 style="margin: 0;">我的更新</n-h2>
      <n-tag v-if="!loading && total != null" size="small" :bordered="false">{{ total }} 条</n-tag>
    </div>
    <n-button size="small" :loading="loading && !!updates.length" :disabled="listBusy" @click="reload">刷新</n-button>
  </div>

  <n-space style="margin-bottom: 16px;">
    <n-radio-group v-model:value="filter" size="small" :disabled="listBusy" @update:value="reload">
      <n-radio-button value="">全部</n-radio-button>
      <n-radio-button value="unread">未读</n-radio-button>
      <n-radio-button value="starred">星标</n-radio-button>
      <n-radio-button value="later">稍后再看</n-radio-button>
    </n-radio-group>
  </n-space>

  <div v-if="loading && !updates.length"><n-spin /></div>
  <n-empty v-else-if="!updates.length" :description="emptyDescription">
    <template #extra>
      <n-space v-if="!filter">
        <n-button type="primary" :disabled="listBusy" @click="router.push('/journals')">浏览期刊</n-button>
        <n-button :disabled="listBusy" @click="router.push('/my/subscriptions')">管理订阅</n-button>
      </n-space>
      <n-button v-else :disabled="listBusy" @click="clearFilter">查看全部更新</n-button>
    </template>
  </n-empty>
  <n-list v-else :style="loading ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
    <n-list-item v-for="u in updates" :key="u.article_id">
      <n-thing>
        <template #header>
          <router-link
            :to="`/articles/${u.article_id}`"
            :style="feedTitleStyle(u)"
            @click="(e: MouseEvent) => { if (loading || originalClickBusy.has(u.article_id) || busyMap[u.article_id]) e.preventDefault() }"
          >
            <span :style="{ fontWeight: u.status.is_read ? 400 : 600 }">{{ u.title }}</span>
          </router-link>
        </template>
        <template #description>
          <n-space size="small" style="margin-top: 4px;">
            <router-link
              v-if="u.journal_id"
              :to="`/journals/${u.journal_id}`"
              :style="journalNavStyle(u.article_id)"
              @click="(e: MouseEvent) => { if (loading || originalClickBusy.has(u.article_id) || busyMap[u.article_id]) e.preventDefault() }"
            >
              <n-tag size="tiny" :bordered="false">{{ u.journal_name }}</n-tag>
            </router-link>
            <n-tag v-else size="tiny" :bordered="false">{{ u.journal_name }}</n-tag>
            <n-tag v-if="u.content_type === 'preprint'" size="tiny" type="info" :bordered="false">{{ contentTypeLabel(u.content_type) }}</n-tag>
            <n-tag
              v-if="u.journal_source_type"
              :type="sourceTypeTagType(u.journal_source_type)"
              size="tiny"
              :bordered="false"
            >{{ sourceTypeLabel(u.journal_source_type) }}</n-tag>
            <n-tag v-for="r in (u.reasons || [])" :key="r" size="tiny" type="warning" :bordered="false">{{ reasonLabel(r) }}</n-tag>
            <n-tag v-if="u.status.original_clicked_at" size="tiny" type="success" :bordered="false">已点原文</n-tag>
            <span style="color: #888; font-size: 12px;">{{ formatDate(u.publish_date) }}</span>
          </n-space>
          <div v-if="u.authors?.length" style="color: #666; font-size: 13px; margin-top: 4px;">
            {{ formatAuthors(u.authors, 4) }}
          </div>
          <p
            v-if="u.abstract"
            style="color: #999; font-size: 12px; line-height: 1.6; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
          >
            {{ truncateAbstract(u.abstract, 220) }}
          </p>
        </template>
        <template #footer>
          <n-space>
            <n-button size="tiny" quaternary :loading="isBusy(u.article_id, 'is_read')" :disabled="listBusy || originalClickBusy.has(u.article_id)" @click="toggle(u, 'is_read')">
              {{ u.status.is_read ? '标为未读' : '标为已读' }}
            </n-button>
            <n-button size="tiny" quaternary :type="u.status.is_starred ? 'warning' : 'default'" :loading="isBusy(u.article_id, 'is_starred')" :disabled="listBusy || originalClickBusy.has(u.article_id)" @click="toggle(u, 'is_starred')">
              {{ u.status.is_starred ? '取消星标' : '星标' }}
            </n-button>
            <n-button size="tiny" quaternary :type="u.status.is_later ? 'info' : 'default'" :loading="isBusy(u.article_id, 'is_later')" :disabled="listBusy || originalClickBusy.has(u.article_id)" @click="toggle(u, 'is_later')">
              {{ u.status.is_later ? '取消稍后再看' : '稍后再看' }}
            </n-button>
            <router-link
              :to="`/articles/${u.article_id}`"
              :style="(loading || originalClickBusy.has(u.article_id) || busyMap[u.article_id]) ? { opacity: 0.55, pointerEvents: 'none' } : undefined"
              @click="(e: MouseEvent) => { if (loading || originalClickBusy.has(u.article_id) || busyMap[u.article_id]) e.preventDefault() }"
            >详情</router-link>
            <n-button
              v-if="u.doi"
              size="tiny"
              quaternary
              tag="a"
              :href="doiUrl(u.doi)"
              target="_blank" rel="noopener noreferrer"
              :disabled="listBusy || originalClickBusy.has(u.article_id)"
              @click="onOriginalClick(u)"
            >
              DOI
            </n-button>
            <n-button
              v-if="u.original_url || u.url"
              size="tiny"
              quaternary
              tag="a"
              :href="u.original_url || u.url"
              target="_blank" rel="noopener noreferrer"
              :disabled="listBusy || originalClickBusy.has(u.article_id)"
              @click="onOriginalClick(u)"
            >
              原文
            </n-button>
          </n-space>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
  <div v-if="hasMore" style="text-align: center; margin-top: 16px;">
    <n-button :loading="loadingMore" :disabled="loadingMore || listBusy" @click="loadMore">加载更多</n-button>
  </div>
  <div
    v-else-if="!loading && updates.length"
    style="text-align: center; margin-top: 16px; color: #bbb; font-size: 13px;"
  >
    已显示全部
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMyUpdates, type MyUpdateItem } from '@/api/myUpdates'
import { updateArticleStatus, recordOriginalClick } from '@/api/reading'
import { truncateAbstract } from '@/utils/abstract'
import { formatDate } from '@/utils/datetime'
import { doiUrl } from '@/utils/url'
import { reasonLabel, formatAuthors, contentTypeLabel, sourceTypeLabel, sourceTypeTagType } from '@/utils/labels'
import {
  NH2, NSpin, NEmpty, NButton, NList, NListItem, NThing, NTag, NSpace,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const updates = ref<MyUpdateItem[]>([])
/** articleId → field currently in-flight (per-field spinner, row-level disable). */
const busyMap = ref<Record<string, 'is_read' | 'is_starred' | 'is_later'>>({})
const loading = ref(true)
const loadingMore = ref(false)
/** Filters/reload locked while list loads or any row status mutates. */
const listBusy = computed(() => loading.value || Object.keys(busyMap.value).length > 0)
const filter = ref('')
const offset = ref(0)
const limit = 20
const hasMore = ref(false)
const total = ref<number | null>(null)
/** Drop stale feed responses when filter/reset races mid-flight. */
let feedLoadSeq = 0
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false

const FILTER_VALUES = new Set(['', 'unread', 'starred', 'later'])

function applyFilterFromQuery() {
  const raw = typeof route.query.filter === 'string' ? route.query.filter : ''
  filter.value = FILTER_VALUES.has(raw) ? raw : ''
}

function syncFilterToQuery() {
  const next: Record<string, string> = {}
  if (filter.value) next.filter = filter.value
  const cur = route.query
  const same = (cur.filter || undefined) === next.filter
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

const emptyDescription = computed(() => {
  if (filter.value === 'unread') return '没有未读更新'
  if (filter.value === 'starred') return '还没有星标论文'
  if (filter.value === 'later') return '稍后再看列表为空'
  return '暂无更新，去订阅期刊或关键词吧'
})

async function fetchPage(reset: boolean) {
  if (reset) {
    loading.value = true
    offset.value = 0
    total.value = null
  } else {
    if (loadingMore.value || loading.value) return
    loadingMore.value = true
  }
  const seq = ++feedLoadSeq
  try {
    const params: { limit: string; offset: string; filter?: string } = {
      limit: String(limit),
      offset: String(offset.value),
    }
    if (filter.value) params.filter = filter.value
    const res = await getMyUpdates(params)
    if (seq !== feedLoadSeq) return
    if (reset) updates.value = res.updates
    else updates.value.push(...res.updates)
    offset.value += res.updates.length
    if (typeof res.total === 'number') total.value = res.total
    hasMore.value = total.value != null
      ? updates.value.length < total.value
      : res.updates.length >= limit
  } catch (e: any) {
    if (seq !== feedLoadSeq) return
    message.error(e.message || '加载失败')
  } finally {
    if (seq === feedLoadSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

async function reload() {
  if (listBusy.value) return
  syncFilterToQuery()
  await fetchPage(true)
}

function clearFilter() {
  if (listBusy.value) return
  filter.value = ''
  reload()
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || listBusy.value) return
  await fetchPage(false)
}


function isBusy(id: string, field: 'is_read' | 'is_starred' | 'is_later') {
  return busyMap.value[id] === field
}

function feedTitleStyle(u: { article_id: string }) {
  const base: Record<string, string> = { textDecoration: 'none', color: 'inherit' }
  if (loading.value || originalClickBusy.value.has(u.article_id) || busyMap.value[u.article_id]) {
    base.opacity = '0.55'
    base.pointerEvents = 'none'
  }
  return base
}

function journalNavStyle(articleId: string) {
  const base: Record<string, string> = { textDecoration: 'none' }
  if (loading.value || originalClickBusy.value.has(articleId) || busyMap.value[articleId]) {
    base.opacity = '0.55'
    base.pointerEvents = 'none'
  }
  return base
}



const originalClickBusy = ref(new Set<string>())
async function toggle(u: MyUpdateItem, field: 'is_read' | 'is_starred' | 'is_later') {
  if (listBusy.value || busyMap.value[u.article_id] || originalClickBusy.value.has(u.article_id)) return
  const next = !u.status[field]
  busyMap.value = { ...busyMap.value, [u.article_id]: field }
  try {
    const status = await updateArticleStatus(u.article_id, { [field]: next })
    u.status.is_read = status.is_read
    u.status.is_starred = status.is_starred
    u.status.is_later = status.is_later
  } catch (e: any) {
    message.error(e.message || '更新失败')
  } finally {
    const { [u.article_id]: _, ...rest } = busyMap.value
    busyMap.value = rest
  }
}


async function onOriginalClick(u: MyUpdateItem) {
  if (originalClickBusy.value.has(u.article_id) || busyMap.value[u.article_id]) return
  originalClickBusy.value = new Set([...originalClickBusy.value, u.article_id])
  try {
    const status = await recordOriginalClick(u.article_id)
    u.status.is_read = status.is_read
    u.status.is_starred = status.is_starred
    u.status.is_later = status.is_later
    u.status.original_clicked_at = status.original_clicked_at
  } catch {
    // non-blocking
  } finally {
    const next = new Set(originalClickBusy.value)
    next.delete(u.article_id)
    originalClickBusy.value = next
  }
}

watch(
  () => route.query.filter,
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyFilterFromQuery()
    fetchPage(true)
  },
)

onUnmounted(() => { feedLoadSeq++ })
onMounted(() => {
  applyFilterFromQuery()
  fetchPage(true)
})
</script>
