<template>
  <n-card title="登录" style="max-width: 400px; margin: 80px auto;">
    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      @submit.prevent="handleLogin"
    >
      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="form.email" placeholder="user@example.com" autocomplete="username" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="form.password" type="password" show-password-on="click" autocomplete="current-password" />
      </n-form-item>
      <n-button type="primary" block :loading="loading" attr-type="submit">登录</n-button>
    </n-form>
    <p style="margin-top: 12px; text-align: center; color: #888;">
      还没有账号？<router-link :to="{ path: '/register', query: route.query }">注册</router-link>
    </p>
  </n-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { safeRedirect } from '@/utils/url'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const formRef = ref<FormInst | null>(null)

const form = reactive({ email: '', password: '' })
const rules: FormRules = {
  email: { required: true, type: 'email', message: '请输入有效邮箱', trigger: ['input', 'blur'] },
  password: { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
}

onMounted(() => {
  if (auth.isLoggedIn) {
    const redirect = safeRedirect(route.query.redirect)
    router.replace(redirect)
  }
})

async function handleLogin() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    message.success('登录成功')
    const redirect = safeRedirect(route.query.redirect)
    router.push(redirect)
  } catch (e: any) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
