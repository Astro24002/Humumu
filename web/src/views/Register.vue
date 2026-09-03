<template>
  <n-card title="注册" style="max-width: 400px; margin: 80px auto;">
    <n-form
      ref="formRef"
      :model="form"
      :rules="rules"
      @submit.prevent="handleRegister"
    >
      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="form.email" placeholder="user@example.com" autocomplete="username" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="form.password" type="password" show-password-on="click" autocomplete="new-password" />
      </n-form-item>
      <n-form-item label="昵称" path="name">
        <n-input v-model:value="form.name" placeholder="可选" autocomplete="nickname" />
      </n-form-item>
      <n-button type="primary" block :loading="loading" attr-type="submit">注册</n-button>
    </n-form>
    <p style="margin-top: 12px; text-align: center; color: #888;">
      已有账号？<router-link :to="{ path: '/login', query: route.query }">登录</router-link>
    </p>
  </n-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const formRef = ref<FormInst | null>(null)

const form = reactive({ email: '', password: '', name: '' })
const rules: FormRules = {
  email: { required: true, type: 'email', message: '请输入有效邮箱', trigger: ['input', 'blur'] },
  password: { required: true, min: 6, message: '密码至少6位', trigger: ['input', 'blur'] },
}

onMounted(() => {
  if (auth.isLoggedIn) {
    const redirect = (route.query.redirect as string) || '/my'
    router.replace(redirect)
  }
})

async function handleRegister() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await auth.register(form.email, form.password, form.name)
    message.success('注册成功')
    const redirect = (route.query.redirect as string) || '/my'
    router.push(redirect)
  } catch (e: any) {
    message.error(e.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
