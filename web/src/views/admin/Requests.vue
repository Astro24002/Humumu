<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <n-h2 style="margin: 0;">期刊申请审核</n-h2>
    <n-radio-group v-model:value="statusFilter" size="small">
      <n-radio-button value="pending">待审</n-radio-button>
      <n-radio-button value="">全部</n-radio-button>
      <n-radio-button value="approved">已通过</n-radio-button>
      <n-radio-button value="rejected">已拒绝</n-radio-button>
    </n-radio-group>
  </div>
  <n-data-table :columns="columns" :data="filtered" :loading="loading" :pagination="{ pageSize: 20 }" />
  <n-empty
    v-if="!loading && !filtered.length"
    style="margin-top: 24px;"
    :description="statusFilter === 'pending' ? '暂无待审申请' : '当前筛选下暂无申请'"
  />
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  NButton, NSpace, NTag, NDataTable, NH2, NRadioGroup, NRadioButton, NEmpty,
} from 'naive-ui'
import { getRequests, reviewRequest, type JournalRequest } from '@/api/admin'

const message = useMessage()
const dialog = useDialog()
const requests = ref<JournalRequest[]>([])
const loading = ref(true)
const statusFilter = ref('pending')

const filtered = computed(() => {
  if (!statusFilter.value) return requests.value
  return requests.value.filter((r) => r.status === statusFilter.value)
})

const columns = [
  { title: '期刊名', key: 'journal_name' },
  { title: '来源', key: 'source_url', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status',
    render: (row: JournalRequest) => {
      const map: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
      return h(NTag, {
        size: 'small',
        type: row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'error' : 'warning',
      }, { default: () => map[row.status] || row.status })
    },
  },
  { title: '申请时间', key: 'created_at' },
  {
    title: '操作', key: 'actions',
    render: (row: JournalRequest) => row.status === 'pending' ? h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => confirmReview(row, 'approved') }, { default: () => '通过' }),
        h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => confirmReview(row, 'rejected') }, { default: () => '拒绝' }),
      ],
    }) : null,
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
  try {
    await reviewRequest(id, status)
    message.success(status === 'approved' ? '已通过（将创建/复用公开期刊）' : '已拒绝')
    load()
  } catch (e: any) {
    message.error(e.message)
  }
}

async function load() {
  loading.value = true
  try {
    requests.value = (await getRequests()).requests
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
