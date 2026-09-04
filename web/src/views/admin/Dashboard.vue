<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <n-h2 style="margin: 0;">系统概览</n-h2>
    <n-button size="small" :loading="loading" @click="load">刷新</n-button>
  </div>
  <n-spin :show="loading">
    <n-grid :cols="5" :x-gap="16" responsive="screen" item-responsive>
      <n-gi span="5 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/journals')">
          <n-statistic title="期刊数" :value="stats.journal_count" />
        </n-card>
      </n-gi>
      <n-gi span="5 m:1">
        <n-card size="small">
          <n-statistic title="文章数" :value="stats.article_count" />
        </n-card>
      </n-gi>
      <n-gi span="5 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/users')">
          <n-statistic title="用户数" :value="stats.user_count" />
        </n-card>
      </n-gi>
      <n-gi span="5 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="goPendingDirectory">
          <n-statistic title="待审公开源" :value="stats.pending_directory_reviews || 0" />
        </n-card>
      </n-gi>
      <n-gi span="5 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="goPendingRequests">
          <n-statistic title="待审申请" :value="stats.pending_requests" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-spin>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStats, type AdminStats } from '@/api/admin'
import { NH2, NGrid, NGi, NStatistic, NCard, NButton, NSpin, useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const loading = ref(true)
const stats = ref<AdminStats>({
  journal_count: 0,
  article_count: 0,
  user_count: 0,
  pending_requests: 0,
  pending_directory_reviews: 0,
})

function goPendingDirectory() {
  router.push({ path: '/admin/journals', query: { status: 'pending_review' } })
}

function goPendingRequests() {
  router.push({ path: '/admin/requests', query: { status: 'pending' } })
}

/** Drop stale stats responses when refresh is clicked mid-flight. */
let statsLoadSeq = 0

async function load() {
  const seq = ++statsLoadSeq
  loading.value = true
  try {
    const next = await getStats()
    if (seq !== statsLoadSeq) return
    stats.value = next
  } catch (e: any) {
    if (seq !== statsLoadSeq) return
    message.error(e?.message || '加载概览失败')
  } finally {
    if (seq === statsLoadSeq) loading.value = false
  }
}

onMounted(load)
</script>
