<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <n-space size="small" align="center">
      <n-h2 style="margin: 0;">期刊申请审核</n-h2>
      <n-tag v-if="!loading" size="small" :bordered="false">{{ total }} 条</n-tag>
    </n-space>
    <n-space align="center" style="flex-wrap: wrap;">
      <n-radio-group v-model:value="statusFilter" size="small" :disabled="loading" @update:value="onStatusFilterChange">
        <n-radio-button value="pending">{{ requestStatusLabel('pending') }}</n-radio-button>
        <n-radio-button value="">全部</n-radio-button>
        <n-radio-button value="approved">{{ requestStatusLabel('approved') }}</n-radio-button>
        <n-radio-button value="rejected">{{ requestStatusLabel('rejected') }}</n-radio-button>
      </n-radio-group>
      <n-button size="small" :loading="loading" @click="reload">刷新</n-button>
    </n-space>
  </div>
  <n-data-table :columns="columns" :data="requests" :loading="loading" :pagination="false" />
  <n-empty
    v-if="!loading && !requests.length"
    style="margin-top: 24px;"
    :description="statusFilter === 'pending' ? '暂无待审申请' : (statusFilter ? '当前筛选下暂无申请' : '暂无申请')"
  >
    <template #extra>
      <n-button v-if="statusFilter" @click="clearFilter">查看全部申请</n-button>
      <n-button v-else quaternary @click="reload" :loading="loading">刷新</n-button>
    </template>
  </n-empty>
  <n-pagination
    v-if="pageCount > 1 && !loading"
    style="margin-top: 16px;"
    :page="page"
    :page-count="pageCount"
    @update:page="onPageChange"
  />
</template>

<script setup lang="ts">
import { ref, h, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  NButton, NSpace, NTag, NDataTable, NH2, NRadioGroup, NRadioButton, NEmpty, NPagination,
} from 'naive-ui'
import { getRequests, reviewRequest, type JournalRequest } from '@/api/admin'
import { formatDateTime } from '@/utils/datetime'
import { shortUrl } from '@/utils/url'
import { requestStatusLabel, requestStatusTagType } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const requests = ref<JournalRequest[]>([])
const total = ref(0)
const loading = ref(true)
/** Drop stale admin request list responses when status/page change mid-flight. */
let requestsLoadSeq = 0
/** Per-row lock so reviewing one request does not disable sibling rows. */
const busyId = ref<string | null>(null)

function statusFromQuery(): string {
  const raw = route.query.status
  if (typeof raw !== 'string') return 'pending'
  if (raw === 'all') return ''
  return raw
}

const statusFilter = ref(statusFromQuery())
const page = ref(1)
const pageSize = 20
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false

function pageFromQuery(): number {
  const raw = route.query.page
  const n = typeof raw === 'string' ? parseInt(raw, 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : 1
}

function applyFromQuery() {
  statusFilter.value = statusFromQuery()
  page.value = pageFromQuery()
}

const pageCount = computed(() => Math.ceil((total.value || 0) / pageSize) || 1)

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
    syncStatusQuery()
    load()
  }
})

/** Dashboard deep-link ?status=pending (and menu without query → pending default). */
watch(
  () => [route.query.status, route.query.page],
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyFromQuery()
    load()
  },
)

const columns = [
  { title: '期刊名', key: 'journal_name' },
  {
    title: '来源',
    key: 'source_url',
    ellipsis: { tooltip: true },
    render: (row: JournalRequest) => {
      const url = row.source_url || ''
      if (!url) return '—'
      return h(
        'a',
        {
          href: url,
          target: '_blank',
          rel: 'noopener noreferrer',
          title: url,
          style: 'color: inherit;',
        },
        shortUrl(url),
      )
    },
  },
  {
    title: '状态', key: 'status',
    render: (row: JournalRequest) => h(NTag, {
      size: 'small',
      type: requestStatusTagType(row.status),
    }, { default: () => requestStatusLabel(row.status) }),
  },
  {
    title: '申请时间',
    key: 'created_at',
    render: (row: JournalRequest) => formatDateTime(row.created_at),
  },
  {
    title: '操作', key: 'actions',
    render: (row: JournalRequest) => {
      if (row.status !== 'pending') return null
      const rowBusy = busyId.value === row.id
      return h(NSpace, null, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: 'success',
            loading: rowBusy,
            disabled: rowBusy,
            onClick: () => confirmReview(row, 'approved'),
          }, { default: () => '通过' }),
          h(NButton, {
            size: 'small',
            type: 'error',
            ghost: true,
            loading: rowBusy,
            disabled: rowBusy,
            onClick: () => confirmReview(row, 'rejected'),
          }, { default: () => '拒绝' }),
        ],
      })
    },
  },
]

function confirmReview(row: JournalRequest, status: string) {
  const approve = status === 'approved'
  dialog.warning({
    title: approve ? '通过申请' : '拒绝申请',
    content: approve
      ? `确认通过「${row.journal_name}」？将创建或复用公开期刊。`
      : `确认拒绝「${row.journal_name}」？`,
    positiveText: approve ? '通过' : '拒绝',
    negativeText: '取消',
    onPositiveClick: () => review(row.id, status),
  })
}

async function review(id: string, status: string) {
  if (busyId.value === id) return
  busyId.value = id
  try {
    await reviewRequest(id, status)
    message.success(status === 'approved' ? '已通过（将创建/复用公开期刊）' : '已拒绝')
    await load()
  } catch (e: any) {
    message.error(e.message)
  } finally {
    busyId.value = null
  }
}

function syncStatusQuery() {
  // Encode "all" explicitly so a bare /admin/requests still means pending default.
  const nextStatus = statusFilter.value === '' ? 'all' : (statusFilter.value || 'pending')
  const next: Record<string, string> = { status: nextStatus }
  if (page.value > 1) next.page = String(page.value)
  const cur = route.query
  const same =
    (typeof cur.status === 'string' ? cur.status : undefined) === next.status
    && (cur.page || undefined) === next.page
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

function clearFilter() {
  statusFilter.value = ''
  page.value = 1
  syncStatusQuery()
  load()
}

function onStatusFilterChange(v: string) {
  statusFilter.value = v
  page.value = 1
  syncStatusQuery()
  load()
}

function onPageChange(p: number) {
  page.value = p
  syncStatusQuery()
  load()
}

function reload() {
  page.value = 1
  syncStatusQuery()
  load()
}

async function load() {
  const seq = ++requestsLoadSeq
  loading.value = true
  try {
    const res = await getRequests({
      status: statusFilter.value || undefined,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    if (seq !== requestsLoadSeq) return
    requests.value = res.requests
    total.value = typeof res.total === 'number' ? res.total : res.requests.length
  } catch (e: any) {
    if (seq !== requestsLoadSeq) return
    message.error(e?.message || '加载失败')
  } finally {
    if (seq === requestsLoadSeq) loading.value = false
  }
}

onMounted(() => {
  applyFromQuery()
  load()
})
</script>
