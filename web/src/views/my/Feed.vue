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

  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!updates.length" description="暂无更新，去订阅期刊或关键词吧">
    <template #extra>
      <n-button @click="router.push('/journals')">浏览期刊</n-button>
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
            <n-tag size="tiny" :bordered="false">{{ u.journal_name }}</n-tag>
            <n-tag v-if="u.content_type === 'preprint'" size="tiny" type="info" :bordered="false">预印本</n-tag>
            <n-tag v-for="r in u.reasons" :key="r" size="tiny" type="warning" :bordered="false">{{ reasonLabel(r) }}</n-tag>
            <span style="color: #888; font-size: 12px;">{{ u.publish_date || '' }}</span>
          </n-space>
          <div style="color: #666; font-size: 13px; margin-top: 4px;">
            {{ u.authors?.slice(0, 4).join(', ') }}{{ (u.authors?.length || 0) > 4 ? ' 等' : '' }}
          </div>
        </template>
        <template #footer>
          <n-space>
            <n-button size="tiny" quaternary @click="toggle(u, 'is_read')">
              {{ u.status.is_read ? '标为未读' : '已读' }}
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
            >
              原文
            </n-button>
          </n-space>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyUpdates, type MyUpdateItem } from '@/api/myUpdates'
import { updateArticleStatus } from '@/api/reading'
import {
  NH2, NSpin, NEmpty, NButton, NList, NListItem, NThing, NTag, NSpace,
  NRadioGroup, NRadioButton, useMessage,
} from 'naive-ui'

const router = useRouter()
const message = useMessage()
const updates = ref<MyUpdateItem[]>([])
const loading = ref(true)
const filter = ref('')

function reasonLabel(r: string): string {
  const map: Record<string, string> = {
    journal: '期刊',
    author: '作者',
    keyword: '关键词',
  }
  return map[r] || r
}

async function reload() {
  loading.value = true
  try {
    const params: { limit: string; filter?: string } = { limit: '50' }
    if (filter.value) params.filter = filter.value
    const res = await getMyUpdates(params)
    updates.value = res.updates
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
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

onMounted(reload)
</script>
