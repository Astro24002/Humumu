<template>
  <n-h2>个人设置</n-h2>
  <n-card title="推送频率">
    <n-radio-group v-model:value="frequency">
      <n-radio value="realtime">实时推送</n-radio>
      <n-radio value="daily">每日汇总</n-radio>
    </n-radio-group>
    <n-button style="margin-top: 16px;" @click="saveFrequency" :loading="saving">保存</n-button>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { updatePushFrequency } from '@/api/subscriptions'
import { useMessage } from 'naive-ui'
import { NH2, NCard, NRadio, NRadioGroup, NButton } from 'naive-ui'

const auth = useAuthStore()
const message = useMessage()
const frequency = ref(auth.user?.push_frequency || 'realtime')
const saving = ref(false)

onMounted(() => { frequency.value = auth.user?.push_frequency || 'realtime' })

async function saveFrequency() {
  saving.value = true
  try {
    await updatePushFrequency(frequency.value)
    message.success('设置已保存')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>
