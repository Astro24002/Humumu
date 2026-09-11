<template>
  <n-h2>个人设置</n-h2>

  <n-card title="账号" style="margin-bottom: 16px;" :style="hydrateBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
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
            :disabled="settingsBusy || !auth.user?.wechat_openid"
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
    <n-alert
      v-if="accountHasEmail && !auth.user?.wechat_openid"
      type="info"
      :bordered="false"
      style="margin-top: 16px;"
      title="绑定微信小程序"
    >
      打开 Humumu 小程序，用当前邮箱登录即可将微信挂到本账号，用于订阅消息推送。
    </n-alert>
    <div v-if="!accountHasEmail" style="margin-top: 16px;">
      <p style="color: #666; font-size: 13px; margin: 0 0 12px;">
        当前为微信登录占位账号，尚无真实邮箱。绑定后可用邮箱登录网页，并启用邮件推送。推荐路径是先在网页用邮箱注册，再在小程序绑定微信。
      </p>
      <n-form
        ref="bindFormRef"
        :model="bindForm"
        :rules="bindRules"
        label-placement="left"
        label-width="72"
        size="small"
        style="max-width: 420px;"
        :disabled="settingsBusy"
      >
        <n-form-item label="邮箱" path="email">
          <n-input
            v-model:value="bindForm.email"
            placeholder="name@example.com"
            autocomplete="email"
            :disabled="settingsBusy"
          />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="bindForm.password"
            type="password"
            show-password-on="click"
            placeholder="至少 6 位"
            autocomplete="new-password"
            :disabled="settingsBusy"
          />
        </n-form-item>
        <n-form-item label="确认密码" path="confirm">
          <n-input
            v-model:value="bindForm.confirm"
            type="password"
            show-password-on="click"
            placeholder="再输入一次"
            autocomplete="new-password"
            :disabled="settingsBusy"
          />
        </n-form-item>
        <n-button
          type="primary"
          :loading="bindBusy"
          :disabled="settingsBusy"
          @click="submitBindEmail"
        >
          绑定邮箱
        </n-button>
      </n-form>
    </div>
  </n-card>

  <n-card title="默认推送频率" style="margin-bottom: 16px;" :style="hydrateBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
    <p style="color: #666; font-size: 13px; margin-bottom: 12px;">
      新订阅默认跟随此设置；可在「订阅管理」中按期刊覆盖。
    </p>
    <n-radio-group v-model:value="frequency" :disabled="settingsBusy">
      <n-radio value="daily">{{ freqLabel('daily') }}汇总（推荐）</n-radio>
      <n-radio value="realtime">{{ freqLabel('realtime') }}推送</n-radio>
    </n-radio-group>
    <n-button
      style="margin-top: 16px;"
      type="primary"
      :disabled="!frequencyDirty || settingsBusy"
      :loading="saving"
      @click="saveFrequency"
    >
      {{ frequencyDirty ? '保存' : '已保存' }}
    </n-button>
  </n-card>

  <n-card title="我的期刊申请" style="margin-bottom: 16px;" :style="hydrateBusy ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
    <p style="color: #666; font-size: 13px; margin-bottom: 12px;">
      通过「添加 RSS」并选择申请公开后会出现在此；也可在订阅管理中继续添加。
    </p>
    <div v-if="requestsLoading && !myRequests.length" style="padding: 12px 0;"><n-spin size="small" /></div>
    <n-empty v-else-if="!myRequests.length" description="暂无申请记录" size="small">
      <template #extra>
        <n-button size="small" :disabled="settingsBusy" @click="router.push('/my/subscriptions')">去添加 RSS</n-button>
      </template>
    </n-empty>
    <n-list v-else :style="requestsLoading ? { opacity: 0.55, pointerEvents: 'none' } : undefined">
      <n-list-item v-for="r in myRequests" :key="r.id">
        <n-thing :title="r.journal_name">
          <template #description>
            <n-space size="small" align="center" style="flex-wrap: wrap;">
              <n-tag size="small" :type="requestStatusTagType(r.status)" :bordered="false">
                {{ requestStatusLabel(r.status) }}
              </n-tag>
              <span style="color: #888; font-size: 12px;">{{ formatDateTime(r.created_at) }}</span>
              <span v-if="r.source_url" style="color: #999; font-size: 12px;">{{ shortUrl(r.source_url) }}</span>
            </n-space>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>
    <n-button
      style="margin-top: 12px;"
      size="small"
      quaternary
      :loading="requestsLoading"
      :disabled="settingsBusy"
      @click="loadMyRequests"
    >刷新申请</n-button>
  </n-card>

  <n-card title="会话">
    <n-button type="error" ghost :disabled="settingsBusy" @click="handleLogout">退出登录</n-button>
  </n-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { updatePushFrequency } from '@/api/subscriptions'
import { getTemplateSetting, updateTemplateSetting } from '@/api/wechat'
import { getMyJournalRequests, type JournalRequest } from '@/api/journals'
import { freqLabel, isWechatPlaceholderEmail, requestStatusLabel, requestStatusTagType } from '@/utils/labels'
import { formatDateTime } from '@/utils/datetime'
import { shortUrl } from '@/utils/url'
import type { FormInst, FormRules } from 'naive-ui'
import {
  NH2, NCard, NRadio, NRadioGroup, NButton, NDescriptions, NDescriptionsItem, NTag, NSwitch,
  NList, NListItem, NThing, NSpace, NEmpty, NSpin, NForm, NFormItem, NInput, NAlert,
  useMessage, useDialog,
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
const hydrateBusy = ref(true)
const bindBusy = ref(false)
const bindFormRef = ref<FormInst | null>(null)
const bindForm = reactive({ email: '', password: '', confirm: '' })
const bindRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: ['input', 'blur'] },
    { type: 'email', message: '邮箱格式不正确', trigger: ['input', 'blur'] },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: ['input', 'blur'] },
    { min: 6, message: '密码至少 6 位', trigger: ['input', 'blur'] },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: ['input', 'blur'] },
    {
      validator: (_rule, value: string) => {
        if (value !== bindForm.password) return new Error('两次密码不一致')
        return true
      },
      trigger: ['input', 'blur'],
    },
  ],
}
const myRequests = ref<JournalRequest[]>([])
const requestsLoading = ref(false)
/** Drop stale settings hydrations if the page unmounts mid-flight. */
let settingsLoadSeq = 0
let requestsLoadSeq = 0

const accountHasEmail = computed(() => {
  const u = auth.user
  if (!u) return false
  if (typeof u.has_email === 'boolean') return u.has_email
  return !!(u.email && !isWechatPlaceholderEmail(u.email))
})

const frequencyDirty = computed(() => frequency.value !== savedFrequency.value)
const settingsBusy = computed(
  () =>
    saving.value
    || templateBusy.value
    || hydrateBusy.value
    || requestsLoading.value
    || bindBusy.value,
)

function persistUser() {
  if (auth.user) localStorage.setItem('user', JSON.stringify(auth.user))
}

async function loadMyRequests() {
  if (!auth.isLoggedIn) {
    myRequests.value = []
    return
  }
  const seq = ++requestsLoadSeq
  requestsLoading.value = true
  try {
    const res = await getMyJournalRequests()
    if (seq !== requestsLoadSeq) return
    myRequests.value = res.requests || []
  } catch {
    if (seq !== requestsLoadSeq) return
    // non-blocking: keep prior list
  } finally {
    if (seq === requestsLoadSeq) requestsLoading.value = false
  }
}

async function hydrateSettings() {
  if (!auth.isLoggedIn) {
    hydrateBusy.value = false
    return
  }
  const seq = ++settingsLoadSeq
  hydrateBusy.value = true
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
  await loadMyRequests()
  if (seq === settingsLoadSeq) hydrateBusy.value = false
}

onMounted(() => { void hydrateSettings() })
onUnmounted(() => {
  settingsLoadSeq++
  requestsLoadSeq++
})

async function saveFrequency() {
  if (settingsBusy.value || !frequencyDirty.value) return
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
  if (settingsBusy.value || !auth.user?.wechat_openid) return
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

async function submitBindEmail() {
  if (settingsBusy.value || accountHasEmail.value) return
  try {
    await bindFormRef.value?.validate()
  } catch {
    return
  }
  bindBusy.value = true
  try {
    await auth.bindEmail(bindForm.email.trim(), bindForm.password)
    bindForm.email = ''
    bindForm.password = ''
    bindForm.confirm = ''
    message.success('邮箱已绑定，可用邮箱密码登录')
  } catch (e: any) {
    message.error(e?.message || '绑定失败')
  } finally {
    bindBusy.value = false
  }
}

function handleLogout() {
  if (settingsBusy.value) return
  dialog.warning({
    title: '确认退出',
    content: '退出后需要重新登录才能管理订阅与阅读状态。',
    positiveText: '退出',
    negativeText: '取消',
    onPositiveClick: () => {
      if (settingsBusy.value) return
      leaveArmed.value = true
      auth.logout()
      message.success('已退出')
      router.push('/')
    },
  })
}

onBeforeRouteLeave((_to, _from, next) => {
  if (saving.value || templateBusy.value || bindBusy.value) {
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
