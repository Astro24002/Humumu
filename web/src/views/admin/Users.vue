<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <n-space size="small" align="center">
      <n-h2 style="margin: 0;">用户管理</n-h2>
      <n-tag v-if="!loading" size="small" :bordered="false">{{ total }} 人</n-tag>
    </n-space>
    <n-space align="center">
      <n-input
        v-model:value="nameFilter"
        clearable
        placeholder="搜索邮箱 / 昵称"
        style="width: 240px"
        @keyup.enter="reload"
        @clear="reload"
      />
      <n-button :loading="loading" @click="reload">刷新</n-button>
    </n-space>
  </div>
  <n-data-table :columns="columns" :data="users" :loading="loading" :pagination="false" />
  <n-empty
    v-if="!loading && !users.length"
    style="margin-top: 24px;"
    :description="nameFilter.trim() ? '没有匹配的用户' : '暂无用户'"
  >
    <template #extra>
      <n-button v-if="nameFilter.trim()" @click="clearFilter">清除搜索</n-button>
    </template>
  </n-empty>
  <n-pagination
    v-if="pageCount > 1 && !loading"
    style="margin-top: 16px;"
    :page="page"
    :page-count="pageCount"
    @update:page="onPageChange"
  />
</template>

<script setup lang="ts">
import { ref, h, computed, watch, onMounted } from 'vue'
import {
  NTag, NDataTable, NH2, NButton, NSpace, NInput, NEmpty, NPagination,
  useMessage, useDialog,
} from 'naive-ui'
import { getUsers, setUserAdmin, type User } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/datetime'
import { freqLabel, isWechatPlaceholderEmail } from '@/utils/labels'

const message = useMessage()
const dialog = useDialog()
const auth = useAuthStore()
const users = ref<User[]>([])
const total = ref(0)
const loading = ref(true)
/** Drop stale admin user list responses when search/page change mid-flight. */
let usersLoadSeq = 0
const busyId = ref<string | null>(null)
const nameFilter = ref('')
const page = ref(1)
const pageSize = 20

const pageCount = computed(() => Math.ceil((total.value || 0) / pageSize) || 1)

watch(pageCount, (n) => {
  if (page.value > n) {
    page.value = n
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
  nameFilter.value = ''
  reload()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function reload() {
  page.value = 1
  load()
}

async function load() {
  const seq = ++usersLoadSeq
  loading.value = true
  try {
    const res = await getUsers({
      q: nameFilter.value.trim() || undefined,
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

onMounted(load)
</script>
