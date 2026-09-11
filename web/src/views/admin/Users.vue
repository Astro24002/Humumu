<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <n-space size="small" align="center">
      <n-h2 style="margin: 0;">用户管理</n-h2>
      <n-tag v-if="!loading" size="small" :bordered="false">{{ total }} 人</n-tag>
    </n-space>
    <n-space align="center" style="flex-wrap: wrap;">
      <n-input
        v-model:value="nameFilter"
        clearable
        placeholder="搜索邮箱 / 昵称"
        style="width: 240px"
        :disabled="loading || !!busyId"
        @keyup.enter="reload"
        @clear="reload"
      />
      <n-select
        v-model:value="emailFilter"
        clearable
        placeholder="邮箱"
        style="width: 140px"
        :disabled="loading || !!busyId"
        :options="[
          { label: '全部邮箱', value: '' },
          { label: '已绑邮箱', value: 'true' },
          { label: '未绑邮箱', value: 'false' },
        ]"
        @update:value="reload"
      />
      <n-select
        v-model:value="wechatFilter"
        clearable
        placeholder="微信"
        style="width: 140px"
        :disabled="loading || !!busyId"
        :options="[
          { label: '全部微信', value: '' },
          { label: '已绑微信', value: 'true' },
          { label: '未绑微信', value: 'false' },
        ]"
        @update:value="reload"
      />
      <n-select
        v-model:value="adminFilter"
        clearable
        placeholder="角色"
        style="width: 130px"
        :disabled="loading || !!busyId"
        :options="[
          { label: '全部角色', value: '' },
          { label: '管理员', value: 'true' },
          { label: '普通用户', value: 'false' },
        ]"
        @update:value="reload"
      />
      <n-button :loading="loading" :disabled="loading || !!busyId" @click="reload">刷新</n-button>
    </n-space>
  </div>
  <n-data-table :columns="columns" :data="users" :loading="loading" :pagination="false"  :style="(loading || !!busyId) ? { opacity: 0.55, pointerEvents: 'none' } : undefined" />
  <n-empty
    v-if="!loading && !users.length"
    style="margin-top: 24px;"
    :description="hasFilters ? '没有匹配的用户' : '暂无用户'"
  >
    <template #extra>
      <n-button v-if="hasFilters" :disabled="loading || !!busyId" @click="clearFilter">清除筛选</n-button>
    </template>
  </n-empty>
  <n-pagination
    v-if="pageCount > 1 && !loading"
    style="margin-top: 16px;"
    :page="page"
    :page-count="pageCount"
    :disabled="loading || !!busyId"
    @update:page="onPageChange"
  />
</template>

<script setup lang="ts">
import { ref, h, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NTag, NDataTable, NH2, NButton, NSpace, NInput, NEmpty, NPagination, NSelect,
  useMessage, useDialog,
} from 'naive-ui'
import { getUsers, setUserAdmin, type User } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/datetime'
import { freqLabel, isWechatPlaceholderEmail } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const auth = useAuthStore()
const users = ref<User[]>([])
const total = ref(0)
const loading = ref(true)
/** Drop stale admin user list responses when search/page change mid-flight. */
let usersLoadSeq = 0
/** Skip one route→state write when we just pushed query ourselves. */
let suppressQueryApply = false
const busyId = ref<string | null>(null)
const nameFilter = ref('')
const emailFilter = ref<string>('')
const wechatFilter = ref<string>('')
const adminFilter = ref<string>('')
const page = ref(1)
const pageSize = 20
const hasFilters = computed(
  () => !!(nameFilter.value.trim() || emailFilter.value || wechatFilter.value || adminFilter.value),
)

function boolFromQuery(raw: unknown): string {
  if (raw === 'true' || raw === 'false') return raw
  return ''
}

function pageFromQuery(): number {
  const raw = route.query.page
  const n = typeof raw === 'string' ? parseInt(raw, 10) : NaN
  return Number.isFinite(n) && n > 0 ? n : 1
}

function applyFiltersFromQuery() {
  const qq = route.query
  nameFilter.value = typeof qq.q === 'string' ? qq.q : ''
  emailFilter.value = boolFromQuery(qq.has_email)
  wechatFilter.value = boolFromQuery(qq.wechat)
  adminFilter.value = boolFromQuery(qq.role)
  page.value = pageFromQuery()
}

function syncFiltersToQuery() {
  const next: Record<string, string> = {}
  if (nameFilter.value.trim()) next.q = nameFilter.value.trim()
  if (emailFilter.value) next.has_email = emailFilter.value
  if (wechatFilter.value) next.wechat = wechatFilter.value
  if (adminFilter.value) next.role = adminFilter.value
  if (page.value > 1) next.page = String(page.value)
  const cur = route.query
  const same =
    (cur.q || undefined) === next.q
    && (cur.has_email || undefined) === next.has_email
    && (cur.wechat || undefined) === next.wechat
    && (cur.role || undefined) === next.role
    && (cur.page || undefined) === next.page
  if (same) return
  suppressQueryApply = true
  router.replace({ query: next })
}

const pageCount = computed(() => Math.ceil((total.value || 0) / pageSize) || 1)

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
    syncFiltersToQuery()
    load()
  }
})

function emailCell(row: User) {
  if (isWechatPlaceholderEmail(row.email)) {
    return h(NSpace, { size: 'small', align: 'center' }, {
      default: () => [
        h('span', { style: 'color:#888' }, '未绑定邮箱'),
        h(NTag, { size: 'tiny', type: 'warning', bordered: false }, { default: () => '微信' }),
      ],
    })
  }
  return row.email || '—'
}

const columns = [
  {
    title: '邮箱',
    key: 'email',
    ellipsis: { tooltip: true },
    render: (row: User) => emailCell(row),
  },
  { title: '昵称', key: 'name' },
  {
    title: '微信',
    key: 'wechat_openid',
    width: 90,
    render: (row: User) => row.wechat_openid
      ? h(NTag, { size: 'small', type: 'success', bordered: false }, { default: () => '已关联' })
      : h('span', { style: 'color:#bbb' }, '—'),
  },
  {
    title: '模板消息',
    key: 'wechat_template_subscribed',
    width: 100,
    render: (row: User) => {
      if (!row.wechat_openid) return h('span', { style: 'color:#bbb' }, '—')
      return h(
        NTag,
        {
          size: 'small',
          type: row.wechat_template_subscribed ? 'success' : 'warning',
          bordered: false,
        },
        { default: () => (row.wechat_template_subscribed ? '已开启' : '未开启') },
      )
    },
  },
  {
    title: '推送频率', key: 'push_frequency',
    render: (row: User) => h(NTag, { size: 'small' }, {
      default: () => freqLabel(row.push_frequency || 'daily'),
    }),
  },
  {
    title: '角色',
    key: 'is_admin',
    render: (row: User) => h(NTag, { size: 'small', type: row.is_admin ? 'success' : 'default' }, {
      default: () => row.is_admin ? '管理员' : '用户',
    }),
  },
  {
    title: '注册时间',
    key: 'created_at',
    render: (row: User) => formatDateTime(row.created_at),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: User) => {
      const self = auth.user?.id === row.id
      if (self) {
        return h('span', { style: 'color:#888;font-size:12px' }, '当前账号')
      }
      const next = !row.is_admin
      return h(NSpace, null, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: next ? 'primary' : 'warning',
            ghost: true,
            loading: busyId.value === row.id,
            disabled: !!busyId.value,
            onClick: () => confirmToggleAdmin(row, next),
          }, { default: () => next ? '设为管理员' : '取消管理员' }),
        ],
      })
    },
  },
]

function displayUserLabel(row: User): string {
  if (row.name) return row.name
  if (row.email && !isWechatPlaceholderEmail(row.email)) return row.email
  return row.id.slice(0, 8)
}

function confirmToggleAdmin(row: User, isAdmin: boolean) {
  if (busyId.value) return
  const label = displayUserLabel(row)
  dialog.warning({
    title: isAdmin ? '设为管理员' : '取消管理员',
    content: isAdmin
      ? `确认将「${label}」设为管理员？对方将可访问管理后台。`
      : `确认取消「${label}」的管理员权限？`,
    positiveText: isAdmin ? '设为管理员' : '取消权限',
    negativeText: '返回',
    onPositiveClick: () => toggleAdmin(row, isAdmin),
  })
}

async function toggleAdmin(row: User, isAdmin: boolean) {
  if (busyId.value) return
  busyId.value = row.id
  try {
    const updated = await setUserAdmin(row.id, isAdmin)
    row.is_admin = !!updated.is_admin
    message.success(isAdmin ? '已设为管理员' : '已取消管理员')
  } catch (e: any) {
    message.error(e.message || '操作失败')
  } finally {
    busyId.value = null
  }
}

function clearFilter() {
  if (loading.value || busyId.value) return
  nameFilter.value = ''
  emailFilter.value = ''
  wechatFilter.value = ''
  adminFilter.value = ''
  page.value = 1
  syncFiltersToQuery()
  load()
}

function onPageChange(p: number) {
  if (loading.value || busyId.value) return
  page.value = p
  syncFiltersToQuery()
  load()
}

function reload() {
  if (loading.value || busyId.value) return
  page.value = 1
  syncFiltersToQuery()
  load()
}

async function load() {
  const seq = ++usersLoadSeq
  loading.value = true
  try {
    const res = await getUsers({
      q: nameFilter.value.trim() || undefined,
      has_email: emailFilter.value === '' ? undefined : emailFilter.value === 'true',
      wechat_bound: wechatFilter.value === '' ? undefined : wechatFilter.value === 'true',
      is_admin: adminFilter.value === '' ? undefined : adminFilter.value === 'true',
      limit: pageSize,
      offset: (page.value - 1) * pageSize,
    })
    if (seq !== usersLoadSeq) return
    users.value = res.users
    total.value = typeof res.total === 'number' ? res.total : res.users.length
  } catch (e: any) {
    if (seq !== usersLoadSeq) return
    message.error(e?.message || '加载失败')
  } finally {
    if (seq === usersLoadSeq) loading.value = false
  }
}

watch(
  () => [route.query.q, route.query.has_email, route.query.wechat, route.query.role, route.query.page],
  () => {
    if (suppressQueryApply) {
      suppressQueryApply = false
      return
    }
    applyFiltersFromQuery()
    load()
  },
)

onUnmounted(() => { usersLoadSeq++ })
onMounted(() => {
  applyFiltersFromQuery()
  load()
})
</script>
