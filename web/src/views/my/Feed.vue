<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <n-h2 style="margin: 0;">我的更新</n-h2>
  </div>

  <n-space style="margin-bottom: 16px;">
    <n-radio-group v-model:value="filter" size="small" @update:value="reload">
      <n-radio-button value="">全部</n-radio-button>
      <n-radio-button value="unread">未读</n-radio-button>
      <n-radio-button value="starred">星标</n-radio-button>
      <n-radio-button value="later">稍后再看</n-radio-button>
    </n-radio-group>
  </n-space>

  <div v-if="loading && !updates.length"><n-spin /></div>
  <n-empty v-else-if="!updates.length" :description="emptyDescription">
    <template #extra>
      <n-space v-if="!filter">
        <n-button type="primary" @click="router.push('/journals')">浏览期刊</n-button>
        <n-button @click="router.push('/my/subscriptions')">管理订阅</n-button>
      </n-space>
      <n-button v-else @click="filter = ''; reload()">查看全部更新</n-button>
    </template>
  </n-empty>
  <n-list v-else>
    <n-list-item v-for="u in updates" :key="u.article_id">
      <n-thing>
        <template #header>
          <router-link :to="`/articles/${u.article_id}`" style="text-decoration: none; color: inherit;">
            <span :style="{ fontWeight: u.status.is_read ? 400 : 600 }">{{ u.title }}</span>
          </router-link>
        </template>
        <template #description>
          <n-space size="small" style="margin-top: 4px;">
            <router-link
              v-if="u.journal_id"
              :to="`/journals/${u.journal_id}`"
              style="text-decoration: none;"
            >
              <n-tag size="tiny" :bordered="false">{{ u.journal_name }}</n-tag>
            </router-link>
            <n-tag v-else size="tiny" :bordered="false">{{ u.journal_name }}</n-tag>
            <n-tag v-if="u.content_type === 'preprint'" size="tiny" type="info" :bordered="false">预印本</n-tag>
            <n-tag v-for="r in u.reasons" :key="r" size="tiny" type="warning" :bordered="false">{{ reasonLabel(r) }}</n-tag>
            <span style="color: #888; font-size: 12px;">{{ u.publish_date || '' }}</span>
          </n-space>
          <div style="color: #666; font-size: 13px; margin-top: 4px;">
            {{ u.authors?.slice(0, 4).join(', ') }}{{ (u.authors?.length || 0) > 4 ? ' 等' : '' }}
          </div>
          <p
            v-if="u.abstract"
            style="color: #999; font-size: 12px; line-height: 1.6; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
          >
            {{ truncateAbstract(u.abstract, 220) }}
          </p>
        </template>
        <template #footer>
          <n-space>
            <n-button size="tiny" quaternary @click="toggle(u, 'is_read')">
              {{ u.status.is_read ? '标为未读' : '标为已读' }}
            </n-button>
            <n-button size="tiny" quaternary :type="u.status.is_starred ? 'warning' : 'default'" @click="toggle(u, 'is_starred')">
              {{ u.status.is_starred ? '取消星标' : '星标' }}
            </n-button>
            <n-button size="tiny" quaternary :type="u.status.is_later ? 'info' : 'default'" @click="toggle(u, 'is_later')">
              {{ u.status.is_later ? '取消稍后再看' : '稍后再看' }}
            </n-button>
            <router-link :to="`/articles/${u.article_id}`">详情</router-link>
            <n-button
              v-if="u.original_url || u.url"
              size="tiny"
              quaternary
              tag="a"
              :href="u.original_url || u.url"
              target="_blank"
              rel="noopener noreferrer"
              @click="onOriginalClick(u)"
            >
              原文
            </n-button>
          </n-space>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
  <div v-if="hasMore || loadingMore" style="text-align: center; margin-top: 16px;">
    <n-button :loading="loadingMore" :disabled="!hasMore" @click="loadMore">
      {{ hasMore ? '加载更多' : '没有更多了' }}
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyUpdates, type MyUpdateItem } from '@/api/myUpdates'
import { updateArticleStatus, recordOriginalClick } from '@/api/reading'
import { truncateAbstract } from '@/utils/abstract'
import {
  NH2, NSpin, NEmpty, NButton, NList, NListItem, NThing, NTag, NSpace,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const router = useRouter()
const message = useMessage()
const updates = ref<MyUpdateItem[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const filter = ref('')
const offset = ref(0)
const limit = 20
const hasMore = ref(false)

const emptyDescription = computed(() => {
  if (filter.value === 'unread') return '没有未读更新'
  if (filter.value === 'starred') return '还没有星标论文'
  if (filter.value === 'later') return '稍后再看列表为空'
  return '暂无更新，去订阅期刊或关键词吧'
})

function reasonLabel(r: string): string {
  const map: Record<string, string> = {
    journal: '期刊',
    author: '作者',
    keyword: '关键词',
  }
  return map[r] || r
}

async function fetchPage(reset: boolean) {
  if (reset) {
    loading.value = true
    offset.value = 0
  } else {
    loadingMore.value = true
  }
  try {
    const params: { limit: string; offset: string; filter?: string } = {
      limit: String(limit),
      offset: String(offset.value),
    }
    if (filter.value) params.filter = filter.value
    const res = await getMyUpdates(params)
    if (reset) updates.value = res.updates
    else updates.value.push(...res.updates)
    offset.value += res.updates.length
    hasMore.value = res.updates.length >= limit
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function reload() {
  await fetchPage(true)
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value) return
  await fetchPage(false)
}

async function toggle(u: MyUpdateItem, field: 'is_read' | 'is_starred' | 'is_later') {
  const next = !u.status[field]
  try {
    const status = await updateArticleStatus(u.article_id, { [field]: next })
    u.status.is_read = status.is_read
    u.status.is_starred = status.is_starred
    u.status.is_later = status.is_later
  } catch (e: any) {
    message.error(e.message || '更新失败')
  }
}

async function onOriginalClick(u: MyUpdateItem) {
  try {
    await recordOriginalClick(u.article_id)
    if (!u.status.is_read) {
      const status = await updateArticleStatus(u.article_id, { is_read: true })
      u.status.is_read = status.is_read
      u.status.original_clicked_at = status.original_clicked_at
    }
  } catch {
    // non-blocking
  }
}

onMounted(reload)
</script>
