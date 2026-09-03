<template>
  <div>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
      <n-h2 style="margin: 0;">期刊广场</n-h2>
      <n-tag v-if="!loading" size="small" :bordered="false">{{ journals.length }} 源</n-tag>
    </div>

    <n-space vertical style="margin-bottom: 16px;">
      <n-input
        v-model:value="q"
        clearable
        placeholder="搜索期刊名称 / 描述"
        style="max-width: 360px;"
        @keyup.enter="reload"
        @clear="reload"
      >
        <template #suffix>
          <n-button text type="primary" @click="reload">搜索</n-button>
        </template>
      </n-input>
      <n-space align="center">
        <n-radio-group v-model:value="contentType" size="small" @update:value="reload">
          <n-radio-button value="">全部</n-radio-button>
          <n-radio-button value="journal">期刊</n-radio-button>
          <n-radio-button value="preprint">预印本</n-radio-button>
        </n-radio-group>
        <n-select
          v-model:value="major"
          clearable
          placeholder="CAS 大类"
          :options="majorOptions"
          style="width: 160px;"
          size="small"
          @update:value="onMajorChange"
        />
        <n-select
          v-model:value="minor"
          clearable
          placeholder="CAS 小类"
          :options="minorOptions"
          style="width: 160px;"
          size="small"
          :disabled="!major"
          @update:value="reload"
        />
        <n-select
          v-model:value="zone"
          clearable
          placeholder="分区"
          :options="zoneOptions"
          style="width: 100px;"
          size="small"
          @update:value="reload"
        />
        <n-checkbox v-model:checked="topOnly" @update:checked="reload">仅 Top</n-checkbox>
      </n-space>
    </n-space>

    <n-grid :cols="2" :y-gap="16" :x-gap="16">
      <n-gi v-for="j in journals" :key="j.id">
        <n-card :title="j.name" hoverable @click="router.push(`/journals/${j.id}`)">
          <template #header-extra>
            <n-space size="small">
              <n-tag v-if="j.content_type === 'preprint'" type="info" size="small" :bordered="false">预印本</n-tag>
              <n-tag :type="j.source_type === 'arxiv' ? 'info' : 'success'" size="small">
                {{ j.source_type }}
              </n-tag>
              <n-tag
                v-if="j.health_status === 'paused'"
                type="error"
                size="small"
                :bordered="false"
                :title="j.last_error || '抓取已暂停'"
              >
                暂停
              </n-tag>
            </n-space>
          </template>

          <div style="display: flex; gap: 16px; margin-bottom: 8px;">
            <n-statistic label="论文" :value="j.article_count" />
            <n-statistic label="更新" :value="j.last_article_date ? formatDate(j.last_article_date) : '暂无'" />
          </div>

          <p v-if="j.description" style="color: #555; font-size: 13px; line-height: 1.6; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            {{ j.description }}
          </p>

          <p style="color: #888; font-size: 12px; word-break: break-all;">{{ j.source_url }}</p>

          <template #action>
            <template v-if="isLoggedIn">
              <n-button
                v-if="subscribedIds.has(j.id)"
                size="small"
                type="error"
                ghost
                :loading="busyId === j.id"
                @click.stop="handleUnsubscribe(j)"
              >
                已订阅
              </n-button>
              <n-button
                v-else
                size="small"
                type="primary"
                ghost
                :loading="busyId === j.id"
                @click.stop="handleSubscribe(j)"
              >
                订阅
              </n-button>
            </template>
            <n-button size="small" quaternary @click.stop="router.push(`/journals/${j.id}`)">
              浏览论文
            </n-button>
          </template>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!journals.length && !loading" description="暂无可浏览的期刊">
      <template #extra>
        <n-button v-if="isLoggedIn" @click="router.push('/my/subscriptions')">添加 RSS 源</n-button>
        <n-button v-else @click="router.push('/login')">登录后添加源</n-button>
      </template>
    </n-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJournals, type Journal } from '@/api/journals'
import { getCasCategories, type CasCategory } from '@/api/categories'
import {
  subscribeJournal,
  unsubscribeJournal,
  getSubscribedJournals,
} from '@/api/subscriptions'
import { useAuthStore } from '@/stores/auth'
import {
  NH2, NGrid, NGi, NCard, NTag, NEmpty, NButton, NStatistic, NInput, NSpace,
  NRadioGroup, NRadioButton, NSelect, NCheckbox, useMessage,
} from 'naive-ui'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = auth.isLoggedIn
const journals = ref<Journal[]>([])
const loading = ref(true)
const q = ref('')
const contentType = ref('')
const major = ref<string | null>(null)
const minor = ref<string | null>(null)
const zone = ref<string | null>(null)
const topOnly = ref(false)
const categories = ref<CasCategory[]>([])
const subscribedIds = ref<Set<string>>(new Set())
const busyId = ref<string | null>(null)

const majorOptions = computed(() => {
  const set = new Set(categories.value.map(c => c.major).filter(Boolean))
  return [...set].sort().map(m => ({ label: m, value: m }))
})

const minorOptions = computed(() => {
  if (!major.value) return []
  const set = new Set(
    categories.value.filter(c => c.major === major.value).map(c => c.minor).filter(Boolean),
  )
  return [...set].sort().map(m => ({ label: m, value: m }))
})

const zoneOptions = [
  { label: '1 区', value: '1' },
  { label: '2 区', value: '2' },
  { label: '3 区', value: '3' },
  { label: '4 区', value: '4' },
]

function formatDate(d: string): string {
  return d.slice(0, 10)
}

function onMajorChange() {
  minor.value = null
  reload()
}

async function refreshSubscribed() {
  if (!auth.isLoggedIn) {
    subscribedIds.value = new Set()
    return
  }
  try {
    const res = await getSubscribedJournals()
    subscribedIds.value = new Set(res.journals.map((j) => j.id))
  } catch {
    // non-blocking
  }
}

async function handleSubscribe(j: Journal) {
  busyId.value = j.id
  try {
    await subscribeJournal(j.id)
    subscribedIds.value = new Set([...subscribedIds.value, j.id])
    message.success(`已订阅「${j.name}」`)
  } catch (e: any) {
    message.error(e.message || '订阅失败')
  } finally {
    busyId.value = null
  }
}

async function handleUnsubscribe(j: Journal) {
  busyId.value = j.id
  try {
    await unsubscribeJournal(j.id)
    const next = new Set(subscribedIds.value)
    next.delete(j.id)
    subscribedIds.value = next
    message.success(`已取消订阅「${j.name}」`)
  } catch (e: any) {
    message.error(e.message || '取消失败')
  } finally {
    busyId.value = null
  }
}

async function reload() {
  loading.value = true
  try {
    const res = await getJournals({
      q: q.value.trim() || undefined,
      content_type: contentType.value || undefined,
      major: major.value || undefined,
      minor: minor.value || undefined,
      zone: zone.value || undefined,
      top: topOnly.value ? 'true' : undefined,
    })
    journals.value = res.journals
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const cas = await getCasCategories()
    categories.value = cas.categories
  } catch {
    // CAS optional
  }
  await Promise.all([reload(), refreshSubscribed()])
})
</script>
