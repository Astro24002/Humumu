<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px;">
    <n-h2 style="margin: 0;">期刊管理</n-h2>
    <n-space>
      <n-button :loading="loading" @click="reload">刷新</n-button>
      <n-button type="primary" @click="openAdd">新增期刊</n-button>
    </n-space>
  </div>

  <n-space style="margin-bottom: 12px;" align="center">
    <n-input
      v-model:value="nameFilter"
      clearable
      placeholder="搜索名称 / slug / URL"
      style="width: 240px"
      @keyup.enter="reload"
      @clear="reload"
    />
    <n-select
      v-model:value="statusFilter"
      clearable
      placeholder="目录状态"
      style="width: 200px"
      :options="[{ label: '全部', value: '' }, ...directoryOptions]"
      @update:value="reload"
    />
    <n-select
      v-model:value="contentFilter"
      clearable
      placeholder="内容类型"
      style="width: 140px"
      :options="[
        { label: '全部', value: '' },
        { label: contentTypeLabel('journal'), value: 'journal' },
        { label: contentTypeLabel('preprint'), value: 'preprint' },
      ]"
      @update:value="reload"
    />
    <n-select
      v-model:value="sourceFilter"
      clearable
      placeholder="源类型"
      style="width: 140px"
      :options="[
        { label: '全部', value: '' },
        { label: sourceTypeLabel('rss'), value: 'rss' },
        { label: sourceTypeLabel('arxiv'), value: 'arxiv' },
        { label: sourceTypeLabel('cnki'), value: 'cnki' },
      ]"
      @update:value="reload"
    />
    <n-select
      v-model:value="sortBy"
      size="small"
      style="width: 140px"
      :options="sortOptions"
      @update:value="reload"
    />
    <span style="color: #888; font-size: 13px;">{{ total }} 源</span>
  </n-space>

  <n-data-table :columns="columns" :data="journals" :loading="loading" :pagination="false" />
  <n-empty
    v-if="!loading && !journals.length"
    style="margin-top: 24px;"
    :description="hasServerFilters ? '当前筛选下暂无期刊' : '暂无期刊'"
  >
    <template #extra>
      <n-button v-if="hasServerFilters" @click="clearFilters">清除筛选</n-button>
      <n-button v-else type="primary" @click="openAdd">新增期刊</n-button>
    </template>
  </n-empty>
  <n-pagination
    v-if="pageCount > 1 && !loading"
    :page="page"
    :page-count="pageCount"
    style="margin-top: 16px;"
    @update:page="onPageChange"
  />

  <n-modal v-model:show="showModal">
    <n-card style="width: 500px;" :title="editingId ? '编辑期刊' : '新增期刊'" role="dialog">
      <n-form :model="form">
        <n-form-item label="名称"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="标识"><n-input v-model:value="form.slug" /></n-form-item>
        <n-form-item label="源类型">
          <n-select v-model:value="form.source_type" :options="[
            { label: sourceTypeLabel('rss'), value: 'rss' },
            { label: sourceTypeLabel('arxiv'), value: 'arxiv' },
            { label: sourceTypeLabel('cnki'), value: 'cnki' },
          ]" />
        </n-form-item>
        <n-form-item label="内容类型">
          <n-select v-model:value="form.content_type" :options="[
            { label: contentTypeLabel('journal'), value: 'journal' },
            { label: contentTypeLabel('preprint'), value: 'preprint' },
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
import { ref, h, computed, watch, onMounted } from 'vue'
import { dirStatusLabel, dirStatusType, contentTypeLabel, sourceTypeLabel, sourceTypeTagType, healthStatusLabel } from '@/utils/labels'
import { useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  NButton, NTag, NSpace, NPopconfirm, NDataTable, NModal, NCard, NForm, NFormItem,
  NInput, NSelect, NSwitch, NH2, NDropdown, NEmpty, NPagination,
} from 'naive-ui'
import { getAllJournals, createJournal, updateJournal, deleteJournal, setDirectoryStatus } from '@/api/admin'
import type { Journal } from '@/api/journals'
import { formatDateTime } from '@/utils/datetime'

const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const journals = ref<Journal[]>([])
const total = ref(0)
const loading = ref(true)
const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const statusBusy = ref(false)
const deleteBusy = ref(false)
const statusFilter = ref<string>(typeof route.query.status === 'string' ? route.query.status : '')
const contentFilter = ref<string>('')
const sourceFilter = ref<string>('')
const nameFilter = ref('')
const sortBy = ref<'name' | 'articles' | 'updated'>('name')
const page = ref(1)
const pageSize = 20

const pageCount = computed(() => Math.ceil((total.value || 0) / pageSize) || 1)

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
    load()
  }
})

const hasServerFilters = computed(() =>
  Boolean(nameFilter.value.trim() || statusFilter.value || contentFilter.value || sourceFilter.value),
)

const sortOptions = [
  { label: '按名称', value: 'name' },
  { label: '按论文数', value: 'articles' },
  { label: '按最近更新', value: 'updated' },
]

function clearFilters() {
  nameFilter.value = ''
  statusFilter.value = ''
  contentFilter.value = ''
  sourceFilter.value = ''
  page.value = 1
  load()
}

const directoryOptions = [
  { label: dirStatusLabel('public'), value: 'public' },
  { label: dirStatusLabel('private'), value: 'private' },
  { label: dirStatusLabel('pending_review'), value: 'pending_review' },
  { label: dirStatusLabel('rejected'), value: 'rejected' },
  { label: dirStatusLabel('hidden'), value: 'hidden' },
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
  { label: `设为${dirStatusLabel('public')}`, key: 'public' },
  { label: `设为${dirStatusLabel('private')}`, key: 'private' },
  { label: dirStatusLabel('pending_review'), key: 'pending_review' },
  { label: dirStatusLabel('rejected'), key: 'rejected' },
  { label: dirStatusLabel('hidden'), key: 'hidden' },
]


const columns = [
  { title: '名称', key: 'name' },
  { title: '标识', key: 'slug' },
  {
    title: '类型',
    key: 'source_type',
    render: (row: Journal) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NTag, { size: 'small', type: sourceTypeTagType(row.source_type) }, { default: () => sourceTypeLabel(row.source_type) }),
        row.content_type === 'preprint'
          ? h(NTag, { size: 'small', type: 'info' }, { default: () => contentTypeLabel('preprint') })
          : null,
      ],
    }),
  },
  {
    title: '目录',
    key: 'directory_status',
    render: (row: Journal) => h(NTag, { size: 'small', type: dirStatusType(row.directory_status) }, {
      default: () => dirStatusLabel(row.directory_status || 'public'),
    }),
  },
  {
    title: '健康',
    key: 'health',
    render: (row: Journal) => {
      const fails = row.consecutive_failures || 0
      const hs = row.health_status || (fails >= 10 || !row.is_active ? 'paused' : 'ok')
      const label = fails > 0 ? `${fails} 失败` : (hs === 'paused' || !row.is_active ? (hs === 'paused' ? healthStatusLabel('paused') : '停用') : '正常')
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
    render: (row: Journal) => {
      const rowBusy = statusBusy.value || deleteBusy.value
      return h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', disabled: rowBusy, onClick: () => edit(row) }, { default: () => '编辑' }),
          h(NDropdown, {
            options: statusMenu,
            disabled: rowBusy,
            onSelect: (key: string) => confirmChangeStatus(row, key),
          }, {
            default: () => h(NButton, {
              size: 'small',
              ghost: true,
              loading: statusBusy.value,
              disabled: rowBusy,
            }, { default: () => '目录状态' }),
          }),
          h(NPopconfirm, {
            disabled: rowBusy,
            onPositiveClick: () => remove(row.id),
          }, {
            default: () => '确认删除？',
            trigger: () => h(NButton, {
              size: 'small',
              type: 'error',
              ghost: true,
              loading: deleteBusy.value,
              disabled: rowBusy,
            }, { default: () => '删除' }),
          }),
        ],
      })
    },
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

function confirmChangeStatus(row: Journal, status: string) {
  const current = row.directory_status || 'public'
  if (current === status) {
    message.info(`已是「${dirStatusLabel(status)}」`)
    return
  }
  const label = row.name || row.slug || row.id
  const nextLabel = dirStatusLabel(status)
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
    message.success(`目录状态 → ${dirStatusLabel(status)}`)
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
  if (deleteBusy.value) return
  deleteBusy.value = true
  try {
    await deleteJournal(id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error(e.message)
  } finally {
    deleteBusy.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function reload() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const res = await getAllJournals({
      q: nameFilter.value.trim() || undefined,
      content_type: contentFilter.value || undefined,
      source_type: sourceFilter.value || undefined,
      directory_status: statusFilter.value || undefined,
      sort: sortBy.value,
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    journals.value = res.journals
    total.value = typeof res.total === 'number' ? res.total : res.journals.length
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
