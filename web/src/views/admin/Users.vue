<template>
  <n-h2>用户管理</n-h2>
  <n-data-table :columns="columns" :data="users" :loading="loading" />
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NDataTable, NH2, NButton, NSpace, useMessage } from 'naive-ui'
import { getUsers, setUserAdmin, type User } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const auth = useAuthStore()
const users = ref<User[]>([])
const loading = ref(true)
const busyId = ref<string | null>(null)

const columns = [
  { title: '邮箱', key: 'email' },
  { title: '昵称', key: 'name' },
  {
    title: '推送频率', key: 'push_frequency',
    render: (row: User) => h(NTag, { size: 'small' }, {
      default: () => row.push_frequency === 'realtime' ? '实时' : '每日',
    }),
  },
  {
    title: '角色',
    key: 'is_admin',
    render: (row: User) => h(NTag, { size: 'small', type: row.is_admin ? 'success' : 'default' }, {
      default: () => row.is_admin ? '管理员' : '用户',
    }),
  },
  { title: '注册时间', key: 'created_at' },
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
            onClick: () => toggleAdmin(row, next),
          }, { default: () => next ? '设为管理员' : '取消管理员' }),
        ],
      })
    },
  },
]

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

onMounted(async () => {
  try {
    users.value = (await getUsers()).users
  } finally {
    loading.value = false
  }
})
</script>
