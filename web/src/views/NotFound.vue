<template>
  <n-result status="404" title="页面不存在" description="链接可能已失效，或你没有访问权限">
    <template #footer>
      <n-space>
        <n-button @click="router.push('/')">回广场</n-button>
        <n-button type="primary" @click="router.push('/journals')">期刊广场</n-button>
        <n-button v-if="auth.isLoggedIn" @click="router.push('/my')">我的更新</n-button>
      </n-space>
    </template>
  </n-result>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NResult, NButton, NSpace } from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()
</script>
