<template>
  <n-h2>用户管理</n-h2>
  <n-data-table :columns="columns" :data="users" :loading="loading" />
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag, NDataTable, NH2 } from 'naive-ui'
import { getUsers, type User } from '@/api/admin'

const users = ref<User[]>([])
const loading = ref(true)

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
]

onMounted(async () => {
  try {
    users.value = (await getUsers()).users
  } finally {
    loading.value = false
  }
})
</script>
