<template>
  <n-h2>期刊申请审核</n-h2>
  <n-data-table :columns="columns" :data="requests" :loading="loading" />
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { NButton, NSpace, NTag, NDataTable, NH2 } from 'naive-ui'
import { getRequests, reviewRequest, type JournalRequest } from '@/api/admin'

const message = useMessage()
const requests = ref<JournalRequest[]>([])
const loading = ref(true)

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
        h(NButton, { size: 'small', type: 'success', onClick: () => review(row.id, 'approved') }, { default: () => '通过' }),
        h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => review(row.id, 'rejected') }, { default: () => '拒绝' }),
      ],
    }) : null,
  },
]

async function review(id: string, status: string) {
  try {
    await reviewRequest(id, status)
    message.success(status === 'approved' ? '已通过' : '已拒绝')
    load()
  } catch (e: any) {
    message.error(e.message)
  }
}

async function load() {
  loading.value = true
  try {
    requests.value = (await getRequests()).requests
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
