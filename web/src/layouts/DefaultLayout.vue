<template>
  <n-layout position="absolute" style="height: 100%">
    <n-layout-header
      bordered
      style="padding: 0 16px; display: flex; align-items: center; gap: 4px; min-height: 56px; flex-wrap: wrap;"
    >
      <n-h3 style="margin: 0; cursor: pointer; white-space: nowrap;" @click="goHome">📓 Humumu</n-h3>
      <div style="flex: 1; min-width: 8px;" />
      <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 2px;">
        <n-button
          quaternary
          :type="isActive('/') ? 'primary' : 'default'"
          @click="router.push({ path: '/', query: {} })"
        >广场</n-button>
        <n-button
          quaternary
          :type="isActive('/journals') ? 'primary' : 'default'"
          @click="router.push({ path: '/journals', query: {} })"
        >期刊</n-button>
        <template v-if="auth.isLoggedIn">
          <n-button
            quaternary
            :type="isActive('/my', true) ? 'primary' : 'default'"
            @click="router.push({ path: '/my', query: {} })"
          >我的更新</n-button>
          <n-button
            quaternary
            :type="isActive('/my/subscriptions') ? 'primary' : 'default'"
            @click="router.push({ path: '/my/subscriptions', query: {} })"
          >订阅</n-button>
          <n-dropdown trigger="click" :options="userMenuOptions" @select="onUserMenuSelect">
            <n-button quaternary>{{ auth.user?.name || '用户' }}</n-button>
          </n-dropdown>
        </template>
        <template v-else>
          <n-button
            quaternary
            :type="isActive('/login') ? 'primary' : 'default'"
            @click="router.push('/login')"
          >登录</n-button>
          <n-button
            quaternary
            :type="isActive('/register') ? 'primary' : 'default'"
            @click="router.push('/register')"
          >注册</n-button>
        </template>
      </div>
    </n-layout-header>

    <n-layout-content style="padding: 24px; max-width: 960px; margin: 0 auto;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  NLayout, NLayoutHeader, NLayoutContent, NButton, NH3, NDropdown, NIcon, useDialog, useMessage,
} from 'naive-ui'
import {
  SettingsOutline, LogOutOutline, ShieldOutline, NotificationsOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const dialog = useDialog()
const message = useMessage()

function goHome() {
  router.push(auth.isLoggedIn ? { path: '/my', query: {} } : { path: '/', query: {} })
}

/** Highlight current section. exact=true matches only that path. */
function isActive(path: string, exact = false): boolean {
  if (exact) return route.path === path
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

const userMenuOptions = computed(() => {
  const opts = [
    {
      key: 'notifications',
      label: '通知历史',
      icon: () => h(NIcon, null, { default: () => h(NotificationsOutline) }),
    },
    { key: 'settings', label: '设置', icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }) },
  ]
  if (auth.isAdmin) {
    opts.push({
      key: 'admin',
      label: '管理后台',
      icon: () => h(NIcon, null, { default: () => h(ShieldOutline) }),
    })
  }
  opts.push({
    key: 'logout',
    label: '退出',
    icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }),
  })
  return opts
})

function onUserMenuSelect(key: string) {
  if (key === 'notifications') router.push({ path: '/my/notifications', query: {} })
  if (key === 'settings') router.push('/settings')
  if (key === 'admin') router.push('/admin')
  if (key === 'logout') {
    dialog.warning({
      title: '确认退出',
      content: '退出后需要重新登录才能管理订阅与阅读状态。',
      positiveText: '退出',
      negativeText: '取消',
      onPositiveClick: () => {
        auth.logout()
        message.success('已退出')
        router.push({ path: '/', query: {} })
      },
    })
  }
}
</script>
