<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <n-h2 style="margin: 0;">CAS 分类</n-h2>
    <n-button type="primary" @click="showCreate = true">新增分类</n-button>
  </div>

  <n-space style="margin-bottom: 12px;" align="center">
    <n-select
      v-model:value="yearFilter"
      clearable
      placeholder="年份"
      style="width: 120px"
      :options="yearOptions"
    />
    <n-button @click="load" :loading="loading">刷新</n-button>
  </n-space>

  <n-data-table :columns="columns" :data="filtered" :loading="loading" :pagination="{ pageSize: 20 }" />

  <n-modal v-model:show="showCreate">
    <n-card style="width: 480px;" title="新增 CAS 分类" role="dialog">
      <n-form :model="form">
        <n-form-item label="年份">
          <n-input-number v-model:value="form.year" :min="2000" :max="2100" style="width: 100%" />
        </n-form-item>
        <n-form-item label="大类">
          <n-input v-model:value="form.major" placeholder="如 生物学" />
        </n-form-item>
        <n-form-item label="小类">
          <n-input v-model:value="form.minor" placeholder="如 细胞生物学" />
        </n-form-item>
        <n-form-item label="分区">
          <n-select
            v-model:value="form.zone"
            :options="[
              { label: '1 区', value: 1 },
              { label: '2 区', value: 2 },
              { label: '3 区', value: 3 },
              { label: '4 区', value: 4 },
            ]"
          />
        </n-form-item>
        <n-form-item label="Top 期刊">
          <n-switch v-model:value="form.is_top" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showCreate = false">取消</n-button>
        <n-button type="primary" :loading="saving" @click="create">创建</n-button>
      </template>
    </n-card>
  </n-modal>

  <n-divider />

  <n-h3 style="margin-top: 8px;">挂载分类到期刊</n-h3>
  <n-form label-placement="left" :label-width="90" style="max-width: 640px;">
    <n-form-item label="期刊">
      <n-select
        v-model:value="attachJournalId"
        filterable
        placeholder="选择期刊"
        :options="journalOptions"
      />
    </n-form-item>
    <n-form-item label="分类">
      <n-select
        v-model:value="attachCategoryIds"
        multiple
        filterable
        placeholder="选择一个或多个 CAS 分类"
        :options="categoryOptions"
      />
    </n-form-item>
    <n-form-item>
      <n-button type="primary" :loading="attaching" :disabled="!attachJournalId || !attachCategoryIds.length" @click="attach">
        挂载
      </n-button>
    </n-form-item>
  </n-form>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  NButton, NCard, NDataTable, NDivider, NForm, NFormItem, NH2, NH3,
  NInput, NInputNumber, NModal, NSelect, NSpace, NSwitch, NTag,
} from 'naive-ui'
import { getCasCategories, type CasCategory } from '@/api/categories'
import { attachCasCategories, createCasCategory, getAllJournals } from '@/api/admin'
import type { Journal } from '@/api/journals'

const message = useMessage()
const loading = ref(true)
const saving = ref(false)
const attaching = ref(false)
const showCreate = ref(false)

const categories = ref<CasCategory[]>([])
const years = ref<number[]>([])
const journals = ref<Journal[]>([])
const yearFilter = ref<number | null>(null)

const form = ref({
  year: new Date().getFullYear(),
  major: '',
  minor: '',
  zone: 1,
  is_top: false,
})

const attachJournalId = ref<string | null>(null)
const attachCategoryIds = ref<string[]>([])

const yearOptions = computed(() => years.value.map(y => ({ label: String(y), value: y })))
const journalOptions = computed(() =>
  journals.value.map(j => ({ label: j.name, value: j.id })),
)
const categoryOptions = computed(() =>
  categories.value.map(c => ({
    label: `${c.year} · ${c.major}/${c.minor} · ${c.zone}区${c.is_top ? ' · Top' : ''}`,
    value: c.id,
  })),
)

const filtered = computed(() => {
  if (!yearFilter.value) return categories.value
  return categories.value.filter(c => c.year === yearFilter.value)
})

const columns = [
  { title: '年份', key: 'year', width: 80 },
  { title: '大类', key: 'major' },
  { title: '小类', key: 'minor' },
  {
    title: '分区',
    key: 'zone',
    width: 80,
    render: (row: CasCategory) => `${row.zone} 区`,
  },
  {
    title: 'Top',
    key: 'is_top',
    width: 80,
    render: (row: CasCategory) => row.is_top
      ? h(NTag, { size: 'small', type: 'success' }, { default: () => 'Top' })
      : '—',
  },
]

async function load() {
  loading.value = true
  try {
    const [cas, jres] = await Promise.all([getCasCategories(), getAllJournals()])
    categories.value = cas.categories
    years.value = cas.years?.length
      ? cas.years
      : [...new Set(cas.categories.map(c => c.year))].sort((a, b) => b - a)
    journals.value = jres.journals
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.value.major.trim() || !form.value.minor.trim()) {
    message.warning('请填写大类和小类')
    return
  }
  saving.value = true
  try {
    await createCasCategory({
      year: form.value.year,
      major: form.value.major.trim(),
      minor: form.value.minor.trim(),
      zone: form.value.zone,
      is_top: form.value.is_top,
    })
    message.success('已创建')
    showCreate.value = false
    form.value = {
      year: form.value.year,
      major: '',
      minor: '',
      zone: 1,
      is_top: false,
    }
    await load()
  } catch (e: any) {
    message.error(e.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function attach() {
  if (!attachJournalId.value || !attachCategoryIds.value.length) return
  attaching.value = true
  try {
    await attachCasCategories(attachJournalId.value, attachCategoryIds.value)
    message.success('已挂载')
    attachCategoryIds.value = []
  } catch (e: any) {
    message.error(e.message || '挂载失败')
  } finally {
    attaching.value = false
  }
}

onMounted(load)
</script>
