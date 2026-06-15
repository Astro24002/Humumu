<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <n-h2 style="margin: 0;">期刊管理</n-h2>
    <n-button type="primary" @click="openAdd">新增期刊</n-button>
  </div>

  <n-data-table :columns="columns" :data="journals" :loading="loading" :pagination="false" />

  <n-modal v-model:show="showModal">
    <n-card style="width: 500px;" :title="editingId ? '编辑期刊' : '新增期刊'" role="dialog">
      <n-form :model="form">
        <n-form-item label="名称"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="标识"><n-input v-model:value="form.slug" /></n-form-item>
        <n-form-item label="源类型">
          <n-select v-model:value="form.source_type" :options="[{ label: 'RSS', value: 'rss' }, { label: 'arXiv', value: 'arxiv' }]" />
        </n-form-item>
        <n-form-item label="源 URL"><n-input v-model:value="form.source_url" /></n-form-item>
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
import { ref, h, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { NButton, NTag, NSpace, NPopconfirm, NDataTable, NModal, NCard, NForm, NFormItem, NInput, NSelect, NSwitch, NH2 } from 'naive-ui'
import { getAllJournals, createJournal, updateJournal, deleteJournal } from '@/api/admin'
import type { Journal } from '@/api/journals'

const message = useMessage()
const journals = ref<Journal[]>([])
const loading = ref(true)
const showModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)

const form = ref<Partial<Journal>>({ name: '', slug: '', source_type: 'rss', source_url: '', is_active: true })

const columns = [
  { title: '名称', key: 'name' },
  { title: '标识', key: 'slug' },
  { title: '类型', key: 'source_type', render: (row: Journal) => h(NTag, { size: 'small' }, { default: () => row.source_type }) },
  { title: '状态', key: 'is_active', render: (row: Journal) => row.is_active ? '启用' : '禁用' },
  {
    title: '操作', key: 'actions',
    render: (row: Journal) => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => edit(row) }, { default: () => '编辑' }),
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
  form.value = { name: '', slug: '', source_type: 'rss', source_url: '', is_active: true }
  showModal.value = true
}

function edit(row: Journal) {
  editingId.value = row.id
  form.value = { ...row }
  showModal.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateJournal(editingId.value, form.value as Journal)
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
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
