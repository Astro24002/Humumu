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
import { computed, h, onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  NLayout, NLayoutSider, NLayoutHeader, NLayoutContent,
  NButton, NH4, NMenu, NIcon,
} from 'naive-ui'
import { BarChart, BookOutline, PeopleOutline, ClipboardOutline, GridOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const activeKey = computed(() => route.path)
const isMobile = ref(false)
const collapsed = ref(false)

function updateViewport() {
  const mobile = window.innerWidth < 900
  isMobile.value = mobile
  // Auto-collapse on small screens; expand when returning to desktop
  collapsed.value = mobile
}

onMounted(() => {
  updateViewport()
  window.addEventListener('resize', updateViewport)
})
onUnmounted(() => {
  window.removeEventListener('resize', updateViewport)
})

const menuOptions = [
  { key: '/admin', label: '概览', icon: () => h(NIcon, null, { default: () => h(BarChart) }) },
  { key: '/admin/journals', label: '期刊管理', icon: () => h(NIcon, null, { default: () => h(BookOutline) }) },
  { key: '/admin/categories', label: 'CAS 分类', icon: () => h(NIcon, null, { default: () => h(GridOutline) }) },
  { key: '/admin/requests', label: '申请审核', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
  { key: '/admin/users', label: '用户管理', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }) },
]

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
