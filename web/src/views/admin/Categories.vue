<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <n-h2 style="margin: 0;">CAS 分类</n-h2>
    <n-button type="primary" :disabled="loading || saving || attaching" @click="showCreate = true">新增分类</n-button>
  </div>

  <n-space style="margin-bottom: 12px;" align="center">
    <n-select
      v-model:value="yearFilter"
      clearable
      placeholder="年份"
      style="width: 120px"
      :disabled="loading"
      :options="yearOptions"
      @update:value="onYearFilterChange"
    />
    <n-button @click="load" :loading="loading">刷新</n-button>
    <n-tag v-if="!loading" size="small" :bordered="false">{{ categories.length }} 条</n-tag>
  </n-space>

  <n-data-table :columns="columns" :data="categories" :loading="loading" :pagination="{ pageSize: 20 }" />
  <n-empty
    v-if="!loading && !categories.length"
    style="margin-top: 24px;"
    :description="yearFilter ? '该年份暂无分类' : '暂无 CAS 分类；可手动新增，或运行 make seed / python -m scripts.seed_cas_categories 导入示例 facet'"
  >
    <template #extra>
      <n-button v-if="yearFilter" @click="clearYearFilter">清除年份筛选</n-button>
      <n-button v-else type="primary" :disabled="loading || saving || attaching" @click="showCreate = true">新增分类</n-button>
    </template>
  </n-empty>

  <n-modal v-model:show="showCreate" :mask-closable="!saving" :close-on-esc="!saving" @update:show="onCreateModalShow">
    <n-card style="width: 480px;" title="新增 CAS 分类" role="dialog">
      <n-form :model="form" :disabled="saving">
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
        <n-button :disabled="saving" @click="showCreate = false">取消</n-button>
        <n-button type="primary" :loading="saving" :disabled="saving" @click="create">创建</n-button>
      </template>
    </n-card>
  </n-modal>

  <n-divider />

  <n-h3 style="margin-top: 8px;">挂载分类到期刊</n-h3>
  <n-form label-placement="left" :label-width="90" style="max-width: 640px;" :disabled="attaching">
    <n-form-item label="期刊">
      <n-select
        v-model:value="attachJournalId"
        filterable
        remote
        clearable
        placeholder="搜索期刊名称 / slug"
        :loading="journalSearchLoading"
        :options="journalOptions"
        :reset-menu-on-options-change="false"
        @search="onJournalSearch"
        @focus="onJournalFocus"
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
      <n-button type="primary" :loading="attaching" :disabled="attaching || !attachJournalId || !attachCategoryIds.length" @click="attach">
        挂载
      </n-button>
    </n-form-item>
  </n-form>
  <p v-if="!loading && !attachCategories.length" style="color: #888; font-size: 13px; margin-top: 4px; max-width: 640px;">
    尚无可用分类。请先新增，或运行 <code>python -m scripts.seed_cas_categories</code> 导入示例 facet。
  </p>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  NButton, NCard, NDataTable, NDivider, NEmpty, NForm, NFormItem, NH2, NH3,
  NInput, NInputNumber, NModal, NSelect, NSpace, NSwitch, NTag,
} from 'naive-ui'
import { getCasCategories, type CasCategory } from '@/api/categories'
import { attachCasCategories, createCasCategory, getAllJournals } from '@/api/admin'
import type { Journal } from '@/api/journals'
import { sourceTypeLabel } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const loading = ref(true)
const saving = ref(false)
const attaching = ref(false)
const showCreate = ref(false)

const categories = ref<CasCategory[]>([])
/** Unfiltered list for the attach multi-select (independent of year table filter). */
const attachCategories = ref<CasCategory[]>([])
const years = ref<number[]>([])
const journals = ref<Journal[]>([])
const journalSearchLoading = ref(false)
const yearFilter = ref<number | null>(null)
let journalSearchSeq = 0
/** Drop stale CAS table responses when year filter changes mid-flight. */
let categoriesLoadSeq = 0
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false

function yearFromQuery(): number | null {
  const raw = route.query.year
  if (typeof raw !== 'string' || !raw) return null
  const n = parseInt(raw, 10)
  return Number.isFinite(n) ? n : null
}

function applyYearFromQuery() {
  yearFilter.value = yearFromQuery()
}

function syncYearToQuery() {
  const next: Record<string, string> = {}
  if (yearFilter.value != null) next.year = String(yearFilter.value)
  const cur = route.query
  const same = (cur.year || undefined) === next.year
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

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
  journals.value.map(j => {
    const src = sourceTypeLabel(j.source_type)
    return {
      label: src ? `${j.name}（${src}）` : j.name,
      value: j.id,
    }
  }),
)

async function fetchJournalOptions(q = '') {
  const seq = ++journalSearchSeq
  journalSearchLoading.value = true
  try {
    const res = await getAllJournals({
      q: q.trim() || undefined,
      sort: 'name',
      limit: 50,
      offset: 0,
    })
    if (seq !== journalSearchSeq) return
    journals.value = res.journals
  } catch (e: any) {
    if (seq !== journalSearchSeq) return
    message.error(e?.message || '加载期刊失败')
  } finally {
    if (seq === journalSearchSeq) journalSearchLoading.value = false
  }
}

function onJournalSearch(q: string) {
  fetchJournalOptions(q)
}

function onJournalFocus() {
  if (!journals.value.length) fetchJournalOptions('')
}
const categoryOptions = computed(() =>
  attachCategories.value.map(c => ({
    label: `${c.year} · ${c.major}/${c.minor} · ${c.zone}区${c.is_top ? ' · Top' : ''}`,
    value: c.id,
  })),
)

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

function onCreateModalShow(show: boolean) {
  if (!show && saving.value) {
    showCreate.value = true
  }
}

function onYearFilterChange(v: number | null) {
  yearFilter.value = v
  syncYearToQuery()
  load()
}

function clearYearFilter() {
  if (loading.value) return
  yearFilter.value = null
  syncYearToQuery()
  load()
}

async function loadAttachCategories() {
  try {
    const cas = await getCasCategories()
    attachCategories.value = cas.categories
    if (cas.years?.length) {
      years.value = cas.years
    } else if (cas.categories.length) {
      years.value = [...new Set(cas.categories.map(c => c.year))].sort((a, b) => b - a)
    }
  } catch {
    // attach options are best-effort; table load surfaces errors
  }
}

async function load() {
  const seq = ++categoriesLoadSeq
  loading.value = true
  try {
    const cas = await getCasCategories(
      yearFilter.value != null ? { year: yearFilter.value } : undefined,
    )
    if (seq !== categoriesLoadSeq) return
    categories.value = cas.categories
    if (cas.years?.length) {
      years.value = cas.years
    } else if (!yearFilter.value) {
      years.value = [...new Set(cas.categories.map(c => c.year))].sort((a, b) => b - a)
    }
    // Keep attach options complete even when the table is year-filtered.
    if (!yearFilter.value) {
      attachCategories.value = cas.categories
    } else if (!attachCategories.value.length) {
      await loadAttachCategories()
    }
    // Journal attach dropdown loads on focus / remote search (paged).
    if (!journals.value.length) await fetchJournalOptions('')
  } catch (e: any) {
    if (seq !== categoriesLoadSeq) return
    message.error(e.message || '加载失败')
  } finally {
    if (seq === categoriesLoadSeq) loading.value = false
  }
}

async function create() {
  if (saving.value) return
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
    await Promise.all([load(), loadAttachCategories()])
  } catch (e: any) {
    message.error(e.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function attach() {
  if (attaching.value) return
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

watch(
  () => route.query.year,
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyYearFromQuery()
    load()
  },
)

onMounted(() => {
  applyYearFromQuery()
  load()
})
</script>
