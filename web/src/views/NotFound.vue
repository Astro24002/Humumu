<template>
  <n-result status="404" title="页面不存在" description="链接可能已失效，或你没有访问权限">
    <template #footer>
      <n-space>
        <n-button type="primary" @click="goPrimary">{{ primaryLabel }}</n-button>
        <n-button @click="router.push({ path: '/journals', query: {} })">期刊广场</n-button>
        <n-button
          v-if="auth.isLoggedIn"
          @click="router.push({ path: '/my/subscriptions', query: {} })"
        >订阅管理</n-button>
        <n-button v-else @click="router.push({ path: '/login', query: {} })">去登录</n-button>
      </n-space>
    </template>
  </n-result>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NResult, NButton, NSpace } from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()

const primaryLabel = computed(() => (auth.isLoggedIn ? '我的更新' : '回广场'))

function goPrimary() {
  router.push(auth.isLoggedIn ? { path: '/my', query: {} } : { path: '/', query: {} })
}
</script>
