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
      <n-descriptions-item v-if="auth.user?.wechat_openid" label="模板消息">
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          <n-switch
            :value="templateSubscribed"
            :loading="templateBusy"
            :disabled="templateBusy || saving || !auth.user?.wechat_openid"
            @update:value="onTemplateChange"
          />
          <n-tag
            size="small"
            :type="templateSubscribed ? 'success' : 'warning'"
            :bordered="false"
          >{{ templateSubscribed ? '已开启' : '未开启' }}</n-tag>
          <span style="color: #888; font-size: 12px;">
            Web 可开关偏好；首次授权需在小程序内完成。
          </span>
        </div>
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
    <n-radio-group v-model:value="frequency" :disabled="saving || templateBusy">
      <n-radio value="daily">{{ freqLabel('daily') }}汇总（推荐）</n-radio>
      <n-radio value="realtime">{{ freqLabel('realtime') }}推送</n-radio>
    </n-radio-group>
    <n-button
      style="margin-top: 16px;"
      type="primary"
      :disabled="!frequencyDirty || saving || templateBusy"
      :loading="saving"
      @click="saveFrequency"
    >
      {{ frequencyDirty ? '保存' : '已保存' }}
    </n-button>
  </n-card>

  <n-card title="会话">
    <n-button type="error" ghost :disabled="saving || templateBusy" @click="handleLogout">退出登录</n-button>
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updatePushFrequency } from '@/api/subscriptions'
import { getTemplateSetting, updateTemplateSetting } from '@/api/wechat'
import { freqLabel, isWechatPlaceholderEmail } from '@/utils/labels'
import {
  NH2, NCard, NRadio, NRadioGroup, NButton, NDescriptions, NDescriptionsItem, NTag, NSwitch, useMessage, useDialog,
} from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const dialog = useDialog()
function normalizeFrequency(f?: string | null): 'daily' | 'realtime' {
  return f === 'realtime' ? 'realtime' : 'daily'
}

const frequency = ref<'daily' | 'realtime'>(normalizeFrequency(auth.user?.push_frequency))
const savedFrequency = ref(frequency.value)
const saving = ref(false)
const leaveArmed = ref(false)
const templateSubscribed = ref(!!auth.user?.wechat_template_subscribed)
const templateBusy = ref(false)
/** Drop stale settings hydrations if the page unmounts mid-flight. */
let settingsLoadSeq = 0

const accountHasEmail = computed(() => {
  const u = auth.user
  if (!u) return false
  if (typeof u.has_email === 'boolean') return u.has_email
  return !!(u.email && !isWechatPlaceholderEmail(u.email))
})

const frequencyDirty = computed(() => frequency.value !== savedFrequency.value)

function persistUser() {
  if (auth.user) localStorage.setItem('user', JSON.stringify(auth.user))
}

async function hydrateSettings() {
  if (!auth.isLoggedIn) return
  const seq = ++settingsLoadSeq
  try {
    await auth.refreshMe()
  } catch {
    // ignore
  }
  if (seq !== settingsLoadSeq) return
  frequency.value = normalizeFrequency(auth.user?.push_frequency)
  savedFrequency.value = frequency.value
  if (typeof auth.user?.wechat_template_subscribed === 'boolean') {
    templateSubscribed.value = auth.user.wechat_template_subscribed
  }
  if (auth.user?.wechat_openid) {
    try {
      const res = await getTemplateSetting()
      if (seq !== settingsLoadSeq) return
      templateSubscribed.value = res.subscribed
    } catch {
      // keep seeded value
    }
  }
}

onMounted(() => { void hydrateSettings() })
onUnmounted(() => { settingsLoadSeq++ })

async function saveFrequency() {
  if (saving.value || templateBusy.value || !frequencyDirty.value) return
  saving.value = true
  try {
    await updatePushFrequency(frequency.value)
    if (auth.user) {
      auth.user.push_frequency = frequency.value
      persistUser()
    }
    savedFrequency.value = frequency.value
    message.success('设置已保存')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

async function onTemplateChange(val: boolean) {
  if (templateBusy.value || saving.value || !auth.user?.wechat_openid) return
  const prev = templateSubscribed.value
  templateBusy.value = true
  try {
    const res = await updateTemplateSetting(val)
    templateSubscribed.value = res.subscribed
    if (auth.user) {
      auth.user.wechat_template_subscribed = res.subscribed
      persistUser()
    }
    message.success(res.subscribed ? '模板消息已开启' : '模板消息已关闭')
  } catch (e: any) {
    templateSubscribed.value = prev
    message.error(e?.message || '操作失败')
  } finally {
    templateBusy.value = false
  }
}

function handleLogout() {
  if (saving.value || templateBusy.value) return
  dialog.warning({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态。',
    positiveText: '退出',
    negativeText: '取消',
    onPositiveClick: () => {
      if (saving.value || templateBusy.value) return
      leaveArmed.value = true
      auth.logout()
      message.success('已退出')
      router.push('/')
    },
  })
}

onBeforeRouteLeave((_to, _from, next) => {
  if (saving.value || templateBusy.value) {
    next(false)
    return
  }
  if (leaveArmed.value || !frequencyDirty.value) {
    next()
    return
  }
  dialog.warning({
    title: '未保存的更改',
    content: '推送频率已修改但尚未保存，确定离开？',
    positiveText: '离开',
    negativeText: '留下',
    onPositiveClick: () => {
      leaveArmed.value = true
      next()
    },
    onNegativeClick: () => next(false),
    onClose: () => next(false),
  })
})
</script>
