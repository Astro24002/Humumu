<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <n-space size="small" align="center">
      <n-h2 style="margin: 0;">通知历史</n-h2>
      <n-tag v-if="!loading && total != null" size="small" :bordered="false">{{ total }} 条</n-tag>
    </n-space>
    <n-space size="small" align="center" style="flex-wrap: wrap;">
      <n-button size="small" :loading="loading && !!notifs.length" @click="reload">刷新</n-button>
      <n-radio-group v-model:value="channelFilter" size="small" @update:value="onFilterChange">
        <n-radio-button value="">全部渠道</n-radio-button>
        <n-radio-button value="email">{{ channelLabel('email') }}</n-radio-button>
        <n-radio-button value="wechat">{{ channelLabel('wechat') }}</n-radio-button>
      </n-radio-group>
      <n-radio-group v-model:value="statusFilter" size="small" @update:value="onFilterChange">
        <n-radio-button value="">全部状态</n-radio-button>
        <n-radio-button value="sent">{{ notifStatusLabel('sent') }}</n-radio-button>
        <n-radio-button value="failed">{{ notifStatusLabel('failed') }}</n-radio-button>
        <n-radio-button value="pending">{{ notifStatusLabel('pending') }}</n-radio-button>
      </n-radio-group>
    </n-space>
  </div>
  <div v-if="loading && !notifs.length"><n-spin /></div>
  <n-empty v-else-if="!notifs.length" :description="emptyDescription">
    <template #extra>
      <n-button v-if="hasActiveFilters" @click="clearFilters">清除筛选</n-button>
      <n-button v-else @click="router.push('/my/subscriptions')">管理订阅</n-button>
    </template>
  </n-empty>
  <n-list v-else>
    <n-list-item v-for="n in notifs" :key="n.id">
      <n-thing>
        <template #header>
          <div>
            <div v-if="n.article_title" style="font-weight: 500; margin-bottom: 6px;">
              <router-link
                v-if="n.article_id"
                :to="`/articles/${n.article_id}`"
                style="text-decoration: none; color: inherit;"
              >{{ n.article_title }}</router-link>
              <template v-else>{{ n.article_title }}</template>
            </div>
            <n-space size="small" align="center">
              <n-tag :type="channelTagType(n.channel)" size="small">
                {{ channelLabel(n.channel) }}
              </n-tag>
              <n-tag :type="notifStatusTagType(n.status)" size="small">
                {{ notifStatusLabel(n.status) }}
              </n-tag>
              <n-tag
                v-for="r in (n.match_reasons || [])"
                :key="r"
                size="tiny"
                type="warning"
                :bordered="false"
              >
                {{ reasonLabel(r) }}
              </n-tag>
            </n-space>
          </div>
        </template>
        <template #description>
          <span style="color: #888; font-size: 12px;">{{ formatDateTime(n.created_at) }}</span>
          <span v-if="n.error_message" style="color: red; margin-left: 8px;">{{ n.error_message }}</span>
        </template>
        <template #footer>
          <router-link v-if="n.article_id" :to="`/articles/${n.article_id}`">查看文章</router-link>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
  <div v-if="hasMore" style="text-align: center; margin-top: 16px;">
    <n-button :loading="loadingMore" :disabled="loadingMore" @click="loadMore">加载更多</n-button>
  </div>
  <div
    v-else-if="!loading && notifs.length"
    style="text-align: center; margin-top: 16px; color: #bbb; font-size: 13px;"
  >
    已显示全部
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, type Notification } from '@/api/notifications'
import { formatDateTime } from '@/utils/datetime'
import { reasonLabel, notifStatusLabel, notifStatusTagType, channelLabel, channelTagType } from '@/utils/labels'
import {
  NH2, NSpin, NEmpty, NList, NListItem, NThing, NTag, NSpace, NButton,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const router = useRouter()
const message = useMessage()
const notifs = ref<Notification[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const offset = ref(0)
const limit = 20
const hasMore = ref(false)
const total = ref<number | null>(null)
const statusFilter = ref('')
const channelFilter = ref('')
/** Drop stale notification list responses when filters race mid-flight. */
let notifLoadSeq = 0

const hasActiveFilters = computed(() => Boolean(statusFilter.value || channelFilter.value))

const emptyDescription = computed(() => {
  if (hasActiveFilters.value) return '当前筛选下暂无通知'
  return '暂无通知'
})

async function fetchPage(reset: boolean) {
  const seq = ++notifLoadSeq
  if (reset) {
    loading.value = true
    offset.value = 0
    notifs.value = []
    total.value = null
  } else {
    loadingMore.value = true
  }
  try {
    const res = await getNotifications({
      limit: String(limit),
      offset: String(offset.value),
      status: statusFilter.value || undefined,
      channel: channelFilter.value || undefined,
    })
    if (seq !== notifLoadSeq) return
    notifs.value.push(...res.notifications)
    offset.value += res.notifications.length
    if (typeof res.total === 'number') total.value = res.total
    hasMore.value = total.value != null
      ? notifs.value.length < total.value
      : res.notifications.length >= limit
  } catch (e: any) {
    if (seq !== notifLoadSeq) return
    message.error(e?.message || '加载失败')
  } finally {
    if (seq === notifLoadSeq) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function reload() {
  fetchPage(true)
}

function onFilterChange() {
  fetchPage(true)
}

function clearFilters() {
  statusFilter.value = ''
  channelFilter.value = ''
  fetchPage(true)
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value) return
  await fetchPage(false)
}

onMounted(() => fetchPage(true))
</script>
