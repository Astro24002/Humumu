<template>
  <n-h2>通知历史</n-h2>
  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!notifs.length" description="暂无通知" />
  <n-list v-else>
    <n-list-item v-for="n in notifs" :key="n.id">
      <n-thing>
        <template #header>
          <n-tag :type="n.channel === 'email' ? 'primary' : 'success'" size="small">{{ n.channel }}</n-tag>
          <n-tag :type="n.status === 'sent' ? 'success' : n.status === 'failed' ? 'error' : 'warning'" size="small" style="margin-left: 8px;">
            {{ n.status === 'sent' ? '已发送' : n.status === 'failed' ? '失败' : '等待中' }}
          </n-tag>
        </template>
        <template #description>
          {{ n.created_at }}
          <span v-if="n.error_message" style="color: red; margin-left: 8px;">{{ n.error_message }}</span>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNotifications, type Notification } from '@/api/notifications'
import { NH2, NSpin, NEmpty, NList, NListItem, NThing, NTag } from 'naive-ui'

const notifs = ref<Notification[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getNotifications()
    notifs.value = res.notifications
  } finally {
    loading.value = false
  }
})
</script>
