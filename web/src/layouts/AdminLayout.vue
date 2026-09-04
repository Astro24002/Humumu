<template>
  <n-layout position="absolute" has-sider style="height: 100%">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="200"
      :collapsed="collapsed"
      :show-trigger="isMobile ? false : 'bar'"
      @collapse="collapsed = true"
      @expand="collapsed = false"
      content-style="padding: 16px 12px;"
    >
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 8px;">
        <n-h4 v-if="!collapsed" style="margin: 0; white-space: nowrap;">📓 管理后台</n-h4>
        <n-button
          v-if="isMobile"
          quaternary
          size="tiny"
          @click="collapsed = !collapsed"
        >
          {{ collapsed ? '展开' : '收起' }}
        </n-button>
      </div>
      <n-menu
        :value="activeKey"
        :options="menuOptions"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        @update:value="onMenuSelect"
      />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered style="padding: 0 16px; display: flex; align-items: center; height: 56px; gap: 8px;">
        <n-button v-if="isMobile" quaternary size="small" @click="collapsed = !collapsed">
          菜单
        </n-button>
        <span style="font-weight: 600;">管理面板</span>
        <div style="flex: 1" />
        <n-button quaternary size="small" @click="goFront">返回前台</n-button>
      </n-layout-header>

      <n-layout-content style="padding: 16px 24px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h, onMounted, onUnmounted, provide, ref, watch, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getStats } from '@/api/admin'
import {
  NLayout, NLayoutSider, NLayoutHeader, NLayoutContent,
  NButton, NH4, NMenu, NIcon, NBadge,
} from 'naive-ui'
import { BarChart, BookOutline, PeopleOutline, ClipboardOutline, GridOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const activeKey = computed(() => route.path)
const isMobile = ref(false)
const collapsed = ref(false)
const pendingDirectory = ref(0)
const pendingRequests = ref(0)
/** Drop stale stats when route-driven refresh races. */
let pendingLoadSeq = 0

function updateViewport() {
  const mobile = window.innerWidth < 900
  isMobile.value = mobile
  // Auto-collapse on small screens; expand when returning to desktop
  collapsed.value = mobile
}

/** Icon badge works when sider is collapsed; extra label badge when expanded. */
function menuIcon(icon: Component, count: number) {
  const inner = () => h(NIcon, null, { default: () => h(icon) })
  if (count <= 0) return inner
  return () => h(
    NBadge,
    { value: count, max: 99, type: 'warning', offset: [2, -2] },
    { default: inner },
  )
}

function pendingExtra(count: number) {
  if (count <= 0) return undefined
  return () => h(NBadge, { value: count, max: 99, type: 'warning' })
}

const menuOptions = computed(() => {
  // Collapsed: badge on icon. Expanded: badge as menu extra (avoid double).
  const dirCount = pendingDirectory.value
  const reqCount = pendingRequests.value
  const dirIconCount = collapsed.value ? dirCount : 0
  const reqIconCount = collapsed.value ? reqCount : 0
  return [
    { key: '/admin', label: '概览', icon: menuIcon(BarChart, 0) },
    {
      key: '/admin/journals',
      label: '期刊管理',
      icon: menuIcon(BookOutline, dirIconCount),
      extra: collapsed.value ? undefined : pendingExtra(dirCount),
    },
    { key: '/admin/categories', label: 'CAS 分类', icon: menuIcon(GridOutline, 0) },
    {
      key: '/admin/requests',
      label: '申请审核',
      icon: menuIcon(ClipboardOutline, reqIconCount),
      extra: collapsed.value ? undefined : pendingExtra(reqCount),
    },
    { key: '/admin/users', label: '用户管理', icon: menuIcon(PeopleOutline, 0) },
  ]
})

function applyPendingCounts(dir: number, req: number) {
  pendingDirectory.value = dir || 0
  pendingRequests.value = req || 0
}

async function loadPendingCounts() {
  const seq = ++pendingLoadSeq
  try {
    const stats = await getStats()
    if (seq !== pendingLoadSeq) return
    applyPendingCounts(stats.pending_directory_reviews || 0, stats.pending_requests || 0)
  } catch {
    // badges are best-effort; leave last known counts
  }
}

provide('refreshAdminPending', loadPendingCounts)
/** Dashboard can push freshly loaded stats without a second hop. */
provide('setAdminPendingCounts', applyPendingCounts)

onMounted(() => {
  updateViewport()
  window.addEventListener('resize', updateViewport)
  loadPendingCounts()
})
onUnmounted(() => {
  window.removeEventListener('resize', updateViewport)
})

// Refresh queue badges when moving between admin sections (e.g. after review).
watch(
  () => route.path,
  (path, prev) => {
    if (path.startsWith('/admin') && path !== prev) loadPendingCounts()
  },
)

function goFront() {
  router.push(auth.isLoggedIn ? '/my' : '/')
}

function onMenuSelect(key: string) {
  // Drop query filters so sidebar nav lands on the section default
  // (e.g. journals without ?status=, requests → pending via empty query).
  router.push({ path: key, query: {} })
  if (isMobile.value) collapsed.value = true
}
</script>
