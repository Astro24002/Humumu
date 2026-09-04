<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <n-h2 style="margin: 0;">系统概览</n-h2>
    <n-button size="small" :loading="loading" :disabled="loading" @click="reload">刷新</n-button>
  </div>
  <n-spin :show="loading">
    <n-grid :cols="6" :x-gap="16" responsive="screen" item-responsive>
      <n-gi span="6 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/journals')">
          <n-statistic title="期刊数" :value="stats.journal_count" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:1">
        <n-card size="small">
          <n-statistic title="文章数" :value="stats.article_count" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/users')">
          <n-statistic title="用户数" :value="stats.user_count" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:1">
        <n-card size="small" hoverable style="cursor: pointer" @click="router.push('/admin/categories')">
          <n-statistic title="CAS 分类" :value="stats.cas_category_count || 0" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:1">
        <n-card
          size="small"
          hoverable
          style="cursor: pointer"
          :class="{ 'stat-attention': (stats.pending_directory_reviews || 0) > 0 }"
          @click="goPendingDirectory"
        >
          <n-statistic title="待审公开源" :value="stats.pending_directory_reviews || 0" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:1">
        <n-card
          size="small"
          hoverable
          style="cursor: pointer"
          :class="{ 'stat-attention': stats.pending_requests > 0 }"
          @click="goPendingRequests"
        >
          <n-statistic title="待审申请" :value="stats.pending_requests" />
        </n-card>
      </n-gi>
    </n-grid>

    <n-alert
      v-if="!loading && (stats.cas_category_count || 0) === 0"
      type="info"
      style="margin-top: 16px;"
      :bordered="false"
      title="CAS 分类为空"
    >
      广场 CAS 筛选与挂载需要 facet 数据。可运行
      <code>make seed-cas</code>
      （含示例期刊挂载）或
      <code>python -m scripts.seed_cas_categories --attach</code>
      导入示例，或在
      <n-button text type="primary" @click="router.push('/admin/categories')">CAS 分类</n-button>
      中手动新增。
    </n-alert>
    <n-alert
      v-if="!loading && stats.journal_count === 0"
      type="info"
      style="margin-top: 12px;"
      :bordered="false"
      title="期刊目录为空"
    >
      可运行
      <code>make seed</code>
      导入内置公开源，或在
      <n-button text type="primary" @click="router.push('/admin/journals')">期刊管理</n-button>
      中新增。
    </n-alert>
  </n-spin>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { getStats, type AdminStats } from '@/api/admin'
import { NH2, NGrid, NGi, NStatistic, NCard, NButton, NSpin, NAlert, useMessage } from 'naive-ui'

const router = useRouter()
const message = useMessage()
const setAdminPendingCounts = inject<(dir: number, req: number) => void>(
  'setAdminPendingCounts',
  () => {},
)
const loading = ref(true)
const stats = ref<AdminStats>({
  journal_count: 0,
  article_count: 0,
  user_count: 0,
  pending_requests: 0,
  pending_directory_reviews: 0,
  cas_category_count: 0,
})

function goPendingDirectory() {
  router.push({ path: '/admin/journals', query: { status: 'pending_review' } })
}

function goPendingRequests() {
  router.push({ path: '/admin/requests', query: { status: 'pending' } })
}

/** Drop stale stats responses when refresh is clicked mid-flight. */
let statsLoadSeq = 0

function reload() {
  if (loading.value) return
  load()
}

async function load() {
  const seq = ++statsLoadSeq
  loading.value = true
  try {
    const next = await getStats()
    if (seq !== statsLoadSeq) return
    stats.value = next
    // Keep sidebar badges aligned without a second /admin/stats hop.
    setAdminPendingCounts(next.pending_directory_reviews || 0, next.pending_requests || 0)
  } catch (e: any) {
    if (seq !== statsLoadSeq) return
    message.error(e?.message || '加载概览失败')
  } finally {
    if (seq === statsLoadSeq) loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stat-attention {
  box-shadow: inset 3px 0 0 #f0a020;
}
</style>
