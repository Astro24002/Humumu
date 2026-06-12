<template>
  <n-h2>我的订阅</n-h2>
  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!articles.length" description="你还没有订阅任何期刊">
    <template #extra>
      <n-button @click="router.push('/journals')">浏览期刊</n-button>
    </template>
  </n-empty>
  <n-list v-else>
    <n-list-item v-for="a in articles" :key="a.id">
      <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
        <template #footer><router-link :to="`/articles/${a.id}`">查看详情</router-link></template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyFeed, type Article } from '@/api/articles'
import { NH2, NSpin, NEmpty, NButton, NList, NListItem, NThing } from 'naive-ui'

const router = useRouter()
const articles = ref<Article[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getMyFeed()
    articles.value = res.articles
  } finally {
    loading.value = false
  }
})
</script>
