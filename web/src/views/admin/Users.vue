<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <n-h2 style="margin: 0;">用户管理</n-h2>
    <n-input
      v-model:value="nameFilter"
      clearable
      placeholder="搜索邮箱 / 昵称"
      style="width: 240px"
    />
  </div>
  <n-data-table :columns="columns" :data="filteredUsers" :loading="loading" :pagination="{ pageSize: 20 }" />
</template>

<script setup lang="ts">
import { ref, h, computed, onMounted } from 'vue'
import { NTag, NDataTable, NH2, NButton, NSpace, NInput, useMessage } from 'naive-ui'
import { getUsers, setUserAdmin, type User } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const auth = useAuthStore()
const users = ref<User[]>([])
const loading = ref(true)
const busyId = ref<string | null>(null)
const nameFilter = ref('')

const filteredUsers = computed(() => {
  const q = nameFilter.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => {
    const hay = `${u.email || ''} ${u.name || ''}`.toLowerCase()
    return hay.includes(q)
  })
})

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
