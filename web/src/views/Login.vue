<template>
  <n-card title="邮箱登录" style="max-width: 400px; margin: 80px auto;">
    <p style="color: #666; font-size: 13px; margin: 0 0 16px; line-height: 1.6;">
      使用注册邮箱登录。微信绑定请在小程序内用同一邮箱完成。
    </p>
    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      @submit.prevent="handleLogin"
    >
      <n-form-item label="邮箱" path="email">
        <n-input
          v-model:value="form.email"
          placeholder="user@example.com"
          autocomplete="username"
          :disabled="loading"
        />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input
          v-model:value="form.password"
          type="password"
          show-password-on="click"
          autocomplete="current-password"
          :disabled="loading"
        />
      </n-form-item>
      <n-button type="primary" block :loading="loading" :disabled="loading" attr-type="submit">登录</n-button>
    </n-form>
    <p style="margin-top: 12px; text-align: center; color: #888;" :style="loading ? 'pointer-events: none; opacity: 0.55;' : undefined">
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
  password: { required: true, min: 6, message: '密码至少6位', trigger: ['input', 'blur'] },
}

onMounted(() => {
  if (auth.isLoggedIn) {
    const redirect = safeRedirect(route.query.redirect)
    router.replace(redirect)
  }
})

async function handleLogin() {
  if (loading.value) return
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
