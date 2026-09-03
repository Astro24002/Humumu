<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>

  <div v-if="loading"><n-spin /></div>
  <template v-else-if="journal">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
      <n-h2 style="margin-bottom: 0;">{{ journal.name }}</n-h2>
      <n-tag v-if="journal.content_type === 'preprint'" type="info" size="small" :bordered="false">预印本</n-tag>
      <n-tag :type="journal.source_type === 'arxiv' ? 'info' : 'success'" size="small">
        {{ journal.source_type }}
      </n-tag>
    </div>

    <n-descriptions label-placement="left" :column="3" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="论文总数">
        <n-number-animation :from="0" :to="journal.article_count" />
      </n-descriptions-item>
      <n-descriptions-item label="数据源">
        <a :href="journal.source_url" target="_blank" style="word-break: break-all;">{{ journal.source_url.slice(0, 60) }}...</a>
      </n-descriptions-item>
      <n-descriptions-item label="最新论文">
        {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}
      </n-descriptions-item>
      <n-descriptions-item v-if="journal.homepage_url" label="主页">
        <a :href="journal.homepage_url" target="_blank" rel="noopener noreferrer">{{ journal.homepage_url }}</a>
      </n-descriptions-item>
    </n-descriptions>

    <n-card v-if="journal.description" size="small" style="margin-bottom: 16px;">
      <template #header><strong>📖 期刊介绍</strong></template>
      {{ journal.description }}
    </n-card>

    <div style="margin-bottom: 16px;">
      <n-button v-if="isLoggedIn" type="primary" ghost @click="handleSubscribe">
        订阅此期刊
      </n-button>
    </div>

    <n-divider />

    <n-h3>论文列表</n-h3>
    <n-empty v-if="!articles.length" description="暂无文章" />
    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing :title="a.title">
          <template #description>
            <span style="color: #888; font-size: 13px;">作者：{{ a.authors?.slice(0, 3).join(', ') }}{{ a.authors?.length > 3 ? ' 等' : '' }}</span>
            <br>
            <span style="color: #aaa; font-size: 12px;">{{ a.publish_date || '' }}</span>
          </template>
          <template #footer>
            <router-link :to="`/articles/${a.id}`">查看详情</router-link>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { subscribeJournal } from '@/api/subscriptions'
import { useAuthStore } from '@/stores/auth'
import {
  NH2, NH3, NButton, NCard, NTag, NDivider, NSpin, NEmpty,
  NList, NListItem, NThing, NDescriptions, NDescriptionsItem,
  NNumberAnimation, useMessage
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = auth.isLoggedIn
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)

function formatDate(d: string): string {
  return d.slice(0, 10)
}

async function handleSubscribe() {
  if (!journal.value) return
  try {
    await subscribeJournal(journal.value.id)
    message.success(`已订阅「${journal.value.name}」`)
  } catch (e: any) {
    message.error(e?.response?.data?.error || '订阅失败')
  }
}

onMounted(async () => {
  try {
    journal.value = await getJournal(route.params.id as string)
    const res = await getArticles({ journal_id: route.params.id as string, limit: '50' })
    articles.value = res.articles
  } finally {
    loading.value = false
  }
})
</script>
