<template>
  <n-h2>个人设置</n-h2>

  <n-card title="账号" style="margin-bottom: 16px;">
    <n-descriptions label-placement="left" :column="1" size="small" bordered>
      <n-descriptions-item label="昵称">
        {{ auth.user?.name || '—' }}
      </n-descriptions-item>
      <n-descriptions-item label="邮箱">
        <template v-if="accountHasEmail">
          {{ auth.user?.email }}
        </template>
        <template v-else>
          <span style="color: #888;">未绑定邮箱</span>
          <n-tag size="tiny" type="warning" :bordered="false" style="margin-left: 8px;">微信登录</n-tag>
        </template>
      </n-descriptions-item>
      <n-descriptions-item label="微信">
        <n-tag v-if="auth.user?.wechat_openid" size="small" type="success" :bordered="false">已关联</n-tag>
        <span v-else style="color: #888;">未关联</span>
      </n-descriptions-item>
      <n-descriptions-item v-if="auth.isAdmin" label="角色">
        <n-tag size="small" type="info" :bordered="false">管理员</n-tag>
      </n-descriptions-item>
    </n-descriptions>
    <p v-if="!accountHasEmail" style="color: #888; font-size: 13px; margin: 12px 0 0;">
      微信一键登录账号暂无真实邮箱；邮件推送需绑定邮箱后才会生效（小程序内可绑定）。
    </p>
  </n-card>

  <n-card title="默认推送频率" style="margin-bottom: 16px;">
    <p style="color: #666; font-size: 13px; margin-bottom: 12px;">
      新订阅默认跟随此设置；可在「订阅管理」中按期刊覆盖。
    </p>
    <n-radio-group v-model:value="frequency">
      <n-radio value="daily">每日汇总（推荐）</n-radio>
      <n-radio value="realtime">实时推送</n-radio>
    </n-radio-group>
    <n-button
      style="margin-top: 16px;"
      type="primary"
      :disabled="!frequencyDirty"
      :loading="saving"
      @click="saveFrequency"
    >
      {{ frequencyDirty ? '保存' : '已保存' }}
    </n-button>
  </n-card>

  <n-card title="会话">
    <n-button type="error" ghost @click="handleLogout">退出登录</n-button>
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updatePushFrequency } from '@/api/subscriptions'
import {
  NH2, NCard, NRadio, NRadioGroup, NButton, NDescriptions, NDescriptionsItem, NTag, useMessage, useDialog,
} from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const dialog = useDialog()
const frequency = ref(auth.user?.push_frequency || 'daily')
const savedFrequency = ref(frequency.value)
const saving = ref(false)

const accountHasEmail = computed(() => {
  const u = auth.user
  if (!u) return false
  if (typeof u.has_email === 'boolean') return u.has_email
  return !!(u.email && !u.email.endsWith('@wechat.user'))
})

const frequencyDirty = computed(() => frequency.value !== savedFrequency.value)

onMounted(async () => {
  if (auth.isLoggedIn) {
    try {
      await auth.refreshMe()
    } catch {
      // ignore
    }
  }
  frequency.value = auth.user?.push_frequency || 'daily'
  savedFrequency.value = frequency.value
})

async function saveFrequency() {
  saving.value = true
  try {
    await updatePushFrequency(frequency.value)
    if (auth.user) {
      auth.user.push_frequency = frequency.value
      localStorage.setItem('user', JSON.stringify(auth.user))
    }
    savedFrequency.value = frequency.value
    message.success('设置已保存')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

function handleLogout() {
  dialog.warning({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态。',
    positiveText: '退出',
    negativeText: '取消',
    onPositiveClick: () => {
      auth.logout()
      message.success('已退出')
      router.push('/')
    },
  })
}
</script>
