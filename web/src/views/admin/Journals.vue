<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <n-h2 style="margin: 0;">期刊管理</n-h2>
    <n-button type="primary" @click="openAdd">新增期刊</n-button>
  </div>

  <n-space style="margin-bottom: 12px;" align="center">
    <n-input
      v-model:value="nameFilter"
      clearable
      placeholder="搜索名称 / slug / URL"
      style="width: 240px"
    />
    <n-select
      v-model:value="statusFilter"
      clearable
      placeholder="目录状态"
      style="width: 200px"
      :options="[{ label: '全部', value: '' }, ...directoryOptions]"
    />
    <n-select
      v-model:value="contentFilter"
      clearable
      placeholder="内容类型"
      style="width: 140px"
      :options="[
        { label: '全部', value: '' },
        { label: '期刊', value: 'journal' },
        { label: '预印本', value: 'preprint' },
      ]"
    />
    <span style="color: #888; font-size: 13px;">{{ filteredJournals.length }} / {{ journals.length }}</span>
  </n-space>

  <n-data-table :columns="columns" :data="filteredJournals" :loading="loading" :pagination="{ pageSize: 20 }" />
  <n-empty
    v-if="!loading && !filteredJournals.length"
    style="margin-top: 24px;"
    :description="hasClientFilters ? '当前筛选下暂无期刊' : '暂无期刊'"
  >
    <template #extra>
      <n-button v-if="hasClientFilters" @click="clearClientFilters">清除筛选</n-button>
      <n-button v-else type="primary" @click="openAdd">新增期刊</n-button>
    </template>
  </n-empty>

  <n-modal v-model:show="showModal">
    <n-card style="width: 500px;" :title="editingId ? '编辑期刊' : '新增期刊'" role="dialog">
      <n-form :model="form">
        <n-form-item label="名称"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="标识"><n-input v-model:value="form.slug" /></n-form-item>
        <n-form-item label="源类型">
          <n-select v-model:value="form.source_type" :options="[
            { label: 'RSS', value: 'rss' },
            { label: 'arXiv', value: 'arxiv' },
            { label: '知网 CNKI', value: 'cnki' },
          ]" />
        </n-form-item>
        <n-form-item label="内容类型">
          <n-select v-model:value="form.content_type" :options="[
            { label: '期刊', value: 'journal' },
            { label: '预印本', value: 'preprint' },
          ]" />
        </n-form-item>
        <n-form-item label="目录状态">
          <n-select v-model:value="form.directory_status" :options="directoryOptions" />
        </n-form-item>
        <n-form-item label="源 URL"><n-input v-model:value="form.source_url" /></n-form-item>
        <n-form-item label="主页 URL"><n-input v-model:value="form.homepage_url" placeholder="https://" /></n-form-item>
        <n-form-item label="介绍"><n-input v-model:value="form.description" type="textarea" :rows="2" /></n-form-item>
        <n-form-item label="启用">
          <n-switch v-model:value="form.is_active" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showModal = false">取消</n-button>
        <n-button type="primary" @click="save" :loading="saving">保存</n-button>
      </template>
    </n-card>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  NButton, NTag, NSpace, NPopconfirm, NDataTable, NModal, NCard, NForm, NFormItem,
  NInput, NSelect, NSwitch, NH2, NDropdown, NEmpty,
} from 'naive-ui'
import { getAllJournals, createJournal, updateJournal, deleteJournal, setDirectoryStatus } from '@/api/admin'
import type { Journal } from '@/api/journals'
import { formatDateTime } from '@/utils/datetime'

const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const journals = ref<Journal[]>([])
const loading = ref(true)
const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const statusBusy = ref(false)
const statusFilter = ref<string>(typeof route.query.status === 'string' ? route.query.status : '')
const contentFilter = ref<string>('')
const nameFilter = ref('')

const filteredJournals = computed(() => {
  const q = nameFilter.value.trim().toLowerCase()
  return journals.value.filter((j) => {
    if (statusFilter.value && (j.directory_status || 'public') !== statusFilter.value) return false
    if (contentFilter.value && (j.content_type || 'journal') !== contentFilter.value) return false
    if (q) {
      const hay = `${j.name || ''} ${j.slug || ''} ${j.source_url || ''} ${j.homepage_url || ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

const hasClientFilters = computed(() =>
  Boolean(nameFilter.value.trim() || statusFilter.value || contentFilter.value),
)

function clearClientFilters() {
  nameFilter.value = ''
  statusFilter.value = ''
  contentFilter.value = ''
}

const directoryOptions = [
  { label: '公开 public', value: 'public' },
  { label: '私有 private', value: 'private' },
  { label: '待审 pending_review', value: 'pending_review' },
  { label: '拒绝 rejected', value: 'rejected' },
  { label: '隐藏 hidden', value: 'hidden' },
]

const form = ref<Partial<Journal>>({
  name: '',
  slug: '',
  source_type: 'rss',
  source_url: '',
  homepage_url: '',
  content_type: 'journal',
  directory_status: 'public',
  is_active: true,
})

const statusMenu = [
  { label: '设为公开', key: 'public' },
  { label: '设为私有', key: 'private' },
  { label: '待审', key: 'pending_review' },
  { label: '拒绝', key: 'rejected' },
  { label: '隐藏', key: 'hidden' },
]

function statusType(s?: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (s === 'public') return 'success'
  if (s === 'pending_review') return 'warning'
  if (s === 'rejected' || s === 'hidden') return 'error'
  if (s === 'private') return 'info'
  return 'default'
}

const columns = [
  { title: '名称', key: 'name' },
  { title: '标识', key: 'slug' },
  {
    title: '类型',
    key: 'source_type',
    render: (row: Journal) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NTag, { size: 'small' }, { default: () => row.source_type }),
        row.content_type === 'preprint'
          ? h(NTag, { size: 'small', type: 'info' }, { default: () => 'preprint' })
          : null,
      ],
    }),
  },
  {
    title: '目录',
    key: 'directory_status',
    render: (row: Journal) => h(NTag, { size: 'small', type: statusType(row.directory_status) }, {
      default: () => row.directory_status || 'public',
    }),
  },
  {
    title: '健康',
    key: 'health',
    render: (row: Journal) => {
      const fails = row.consecutive_failures || 0
      const hs = row.health_status || (fails >= 10 || !row.is_active ? 'paused' : 'ok')
      const label = fails > 0 ? `${fails} 失败` : (hs === 'paused' || !row.is_active ? '停用' : '正常')
      const type = fails > 0 || hs === 'paused' ? 'error' : 'success'
      const lastOk = row.last_success_at ? formatDateTime(row.last_success_at) : ''
      const tip = row.last_error
        ? `${label}${lastOk ? ` · 上次成功 ${lastOk}` : ''}\n${row.last_error}`
        : (lastOk ? `上次成功 ${lastOk}` : label)
      return h(NTag, { size: 'small', type, title: tip }, { default: () => label })
    },
  },
  { title: '状态', key: 'is_active', render: (row: Journal) => row.is_active ? '启用' : '禁用' },
  {
    title: '操作',
    key: 'actions',
    render: (row: Journal) => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => edit(row) }, { default: () => '编辑' }),
        h(NDropdown, {
          options: statusMenu,
          onSelect: (key: string) => confirmChangeStatus(row, key),
        }, {
          default: () => h(NButton, { size: 'small', ghost: true }, { default: () => '目录状态' }),
        }),
        h(NPopconfirm, { onPositiveClick: () => remove(row.id) }, {
          default: () => '确认删除？',
          trigger: () => h(NButton, { size: 'small', type: 'error', ghost: true }, { default: () => '删除' }),
        }),
      ],
    }),
  },
]

function openAdd() {
  editingId.value = null
  form.value = {
    name: '',
    slug: '',
    source_type: 'rss',
    source_url: '',
    homepage_url: '',
    content_type: 'journal',
    directory_status: 'public',
    is_active: true,
  }
  showModal.value = true
}

function edit(row: Journal) {
  editingId.value = row.id
  form.value = { ...row }
  showModal.value = true
}

const statusLabels: Record<string, string> = {
  public: '公开',
  private: '私有',
  pending_review: '待审',
  rejected: '拒绝',
  hidden: '隐藏',
}

function confirmChangeStatus(row: Journal, status: string) {
  const current = row.directory_status || 'public'
  if (current === status) {
    message.info(`已是「${statusLabels[status] || status}」`)
    return
  }
  const label = row.name || row.slug || row.id
  const nextLabel = statusLabels[status] || status
  const dangerous = status === 'rejected' || status === 'hidden'
  const content = dangerous
    ? `确认将「${label}」设为${nextLabel}？广场将不再展示该源。`
    : `确认将「${label}」的目录状态改为「${nextLabel}」？`
  const opts = {
    title: `目录状态 → ${nextLabel}`,
    content,
    positiveText: dangerous ? `确认${nextLabel}` : '确认',
    negativeText: '返回',
    onPositiveClick: () => changeStatus(row.id, status),
  }
  if (dangerous) dialog.warning(opts)
  else dialog.info(opts)
}

async function changeStatus(id: string, status: string) {
  if (statusBusy.value) return
  statusBusy.value = true
  try {
    await setDirectoryStatus(id, status)
    message.success(`目录状态 → ${statusLabels[status] || status}`)
    await load()
  } catch (e: any) {
    message.error(e.message)
  } finally {
    statusBusy.value = false
  }
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateJournal(editingId.value, form.value as Journal)
      if (form.value.directory_status) {
        await setDirectoryStatus(editingId.value, form.value.directory_status)
      }
      message.success('已更新')
    } else {
      await createJournal(form.value as Journal)
      message.success('已创建')
    }
    showModal.value = false
    editingId.value = null
    load()
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(id: string) {
  try {
    await deleteJournal(id)
    message.success('已删除')
    load()
  } catch (e: any) {
    message.error(e.message)
  }
}

async function load() {
  loading.value = true
  try {
    journals.value = (await getAllJournals()).journals
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
