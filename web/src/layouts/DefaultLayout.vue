<template>
  <n-layout position="absolute" style="height: 100%">
    <n-layout-header bordered style="padding: 0 24px; display: flex; align-items: center; height: 56px;">
      <n-h3 style="margin: 0; cursor: pointer" @click="goHome">📓 Humumu</n-h3>
      <div style="flex: 1" />
      <n-button quaternary @click="router.push('/')">广场</n-button>
      <n-button quaternary @click="router.push('/journals')">期刊</n-button>
      <template v-if="auth.isLoggedIn">
        <n-button quaternary @click="router.push('/my')">我的更新</n-button>
        <n-button quaternary @click="router.push('/my/subscriptions')">订阅</n-button>
        <n-dropdown trigger="click" :options="userMenuOptions" @select="onUserMenuSelect">
          <n-button quaternary>{{ auth.user?.name || '用户' }}</n-button>
        </n-dropdown>
      </template>
      <template v-else>
        <n-button quaternary @click="router.push('/login')">登录</n-button>
        <n-button quaternary @click="router.push('/register')">注册</n-button>
      </template>
    </n-layout-header>

    <n-layout-content style="padding: 24px; max-width: 960px; margin: 0 auto;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NLayout, NLayoutHeader, NLayoutContent, NButton, NH3, NDropdown, NIcon } from 'naive-ui'
import {
  SettingsOutline, LogOutOutline, ShieldOutline, NotificationsOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const auth = useAuthStore()

function goHome() {
  router.push(auth.isLoggedIn ? '/my' : '/')
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
  if (key === 'notifications') router.push('/my/notifications')
  if (key === 'settings') router.push('/settings')
  if (key === 'admin') router.push('/admin')
  if (key === 'logout') { auth.logout(); router.push('/') }
}
</script>
