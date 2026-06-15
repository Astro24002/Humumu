<template>
  <n-h2>系统概览</n-h2>
  <n-grid :cols="4" :x-gap="16">
    <n-gi><n-statistic title="期刊数" :value="stats.journal_count" /></n-gi>
    <n-gi><n-statistic title="文章数" :value="stats.article_count" /></n-gi>
    <n-gi><n-statistic title="用户数" :value="stats.user_count" /></n-gi>
    <n-gi><n-statistic title="待审批申请" :value="stats.pending_requests" /></n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getStats, type AdminStats } from '@/api/admin'
import { NH2, NGrid, NGi, NStatistic } from 'naive-ui'

const stats = ref<AdminStats>({ journal_count: 0, article_count: 0, user_count: 0, pending_requests: 0 })

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch {}
})
</script>
