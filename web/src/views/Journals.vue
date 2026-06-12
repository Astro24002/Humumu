<template>
  <div>
    <n-h2>期刊广场</n-h2>
    <n-grid :cols="2" :y-gap="16" :x-gap="16">
      <n-gi v-for="j in journals" :key="j.id">
        <n-card :title="j.name" hoverable @click="router.push(`/journals/${j.id}`)">
          <n-tag :type="j.source_type === 'arxiv' ? 'info' : 'success'" size="small">
            {{ j.source_type }}
          </n-tag>
          <p style="margin-top: 8px; color: #888; font-size: 12px;">{{ j.source_url }}</p>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!journals.length && !loading" description="暂无可浏览的期刊" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJournals, type Journal } from '@/api/journals'
import { NH2, NGrid, NGi, NCard, NTag, NEmpty } from 'naive-ui'

const router = useRouter()
const journals = ref<Journal[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    journals.value = (await getJournals()).journals
  } finally {
    loading.value = false
  }
})
</script>
