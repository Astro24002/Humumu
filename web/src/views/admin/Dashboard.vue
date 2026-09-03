<template>
  <n-h2>系统概览</n-h2>
  <n-grid :cols="5" :x-gap="16">
    <n-gi>
      <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/journals')">
        <n-statistic title="期刊数" :value="stats.journal_count" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card size="small">
        <n-statistic title="文章数" :value="stats.article_count" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/users')">
        <n-statistic title="用户数" :value="stats.user_count" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card size="small" hoverable style="cursor: pointer" @click="goPendingDirectory">
        <n-statistic title="待审公开源" :value="stats.pending_directory_reviews || 0" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/requests')">
        <n-statistic title="旧申请队列" :value="stats.pending_requests" />
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStats, type AdminStats } from '@/api/admin'
import { NH2, NGrid, NGi, NStatistic, NCard } from 'naive-ui'

const router = useRouter()
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

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch {}
})
</script>
