<template>
  <n-layout position="absolute" has-sider style="height: 100%">
    <n-layout-sider bordered content-style="padding: 24px;" width="200">
      <n-h4 style="margin-bottom: 16px;">📓 管理后台</n-h4>
      <n-menu :value="activeKey" :options="menuOptions" @update:value="onMenuSelect" />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered style="padding: 0 24px; display: flex; align-items: center; height: 56px;">
        <span style="font-weight: 600;">管理面板</span>
        <div style="flex: 1" />
        <n-button quaternary size="small" @click="router.push('/')">返回前台</n-button>
      </n-layout-header>

      <n-layout-content style="padding: 24px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NButton, NH4, NMenu, NIcon } from 'naive-ui'
import { BarChart, BookOutline, PeopleOutline, ClipboardOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => route.path)

const menuOptions = [
  { key: '/admin', label: '概览', icon: () => h(NIcon, null, { default: () => h(BarChart) }) },
  { key: '/admin/journals', label: '期刊管理', icon: () => h(NIcon, null, { default: () => h(BookOutline) }) },
  { key: '/admin/requests', label: '申请审核', icon: () => h(NIcon, null, { default: () => h(ClipboardOutline) }) },
  { key: '/admin/users', label: '用户管理', icon: () => h(NIcon, null, { default: () => h(PeopleOutline) }) },
]

function onMenuSelect(key: string) {
  router.push(key)
}
</script>
