<template>
  <div>
    <n-h2>期刊广场</n-h2>
    <n-grid :cols="2" :y-gap="16" :x-gap="16">
      <n-gi v-for="j in journals" :key="j.id">
        <n-card :title="j.name" hoverable @click="router.push(`/journals/${j.id}`)">
          <template #header-extra>
            <n-tag :type="j.source_type === 'arxiv' ? 'info' : 'success'" size="small">
              {{ j.source_type }}
            </n-tag>
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
            <n-button v-if="isLoggedIn" size="small" type="primary" ghost
              @click.stop="handleSubscribe(j)">
              订阅
            </n-button>
            <n-button size="small" quaternary @click.stop="router.push(`/journals/${j.id}`)">
              浏览论文
            </n-button>
          </template>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!journals.length && !loading" description="暂无可浏览的期刊" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJournals, type Journal } from '@/api/journals'
import { subscribeJournal } from '@/api/subscriptions'
import { useAuthStore } from '@/stores/auth'
import { NH2, NGrid, NGi, NCard, NTag, NEmpty, NButton, NStatistic, useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = auth.isLoggedIn
const journals = ref<Journal[]>([])
const loading = ref(true)

function formatDate(d: string): string {
  return d.slice(0, 10)
}

async function handleSubscribe(j: Journal) {
  try {
    await subscribeJournal(j.id)
    message.success(`已订阅「${j.name}」`)
  } catch (e: any) {
    message.error(e?.response?.data?.error || '订阅失败')
  }
}

onMounted(async () => {
  try {
    journals.value = (await getJournals()).journals
  } finally {
    loading.value = false
  }
})
</script>
