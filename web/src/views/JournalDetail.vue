<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>

  <div v-if="loading"><n-spin /></div>
  <n-result v-else-if="loadError" status="404" :title="loadError" description="可能是私有源或已删除">
    <template #footer>
      <n-button @click="router.push('/journals')">期刊广场</n-button>
      <n-button type="primary" style="margin-left: 8px;" @click="router.push('/my/subscriptions')">我的订阅</n-button>
    </template>
  </n-result>
  <template v-else-if="journal">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
      <n-h2 style="margin-bottom: 0;">{{ journal.name }}</n-h2>
      <n-tag v-if="journal.content_type === 'preprint'" type="info" size="small" :bordered="false">预印本</n-tag>
      <n-tag :type="journal.source_type === 'arxiv' ? 'info' : 'success'" size="small">
        {{ journal.source_type }}
      </n-tag>
      <n-tag
        v-if="journal.directory_status && journal.directory_status !== 'public'"
        :type="dirStatusType(journal.directory_status)"
        size="small"
        :bordered="false"
      >
        {{ dirStatusLabel(journal.directory_status) }}
      </n-tag>
      <n-tag
        v-if="journal.health_status === 'paused'"
        type="error"
        size="small"
        :bordered="false"
        :title="journal.last_error || '抓取已暂停'"
      >
        抓取暂停
      </n-tag>
    </div>

    <n-descriptions label-placement="left" :column="3" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="论文总数">
        <n-number-animation :from="0" :to="journal.article_count" />
      </n-descriptions-item>
      <n-descriptions-item label="数据源">
        <a :href="journal.source_url" target="_blank" rel="noopener noreferrer" style="word-break: break-all;">{{ shortUrl(journal.source_url) }}</a>
      </n-descriptions-item>
      <n-descriptions-item label="最新论文">
        {{ journal.last_article_date ? formatDate(journal.last_article_date) : '暂无' }}
      </n-descriptions-item>
      <n-descriptions-item v-if="journal.homepage_url" label="主页">
        <a :href="journal.homepage_url" target="_blank" rel="noopener noreferrer">{{ shortUrl(journal.homepage_url) }}</a>
      </n-descriptions-item>
    </n-descriptions>

    <n-card v-if="journal.description" size="small" style="margin-bottom: 16px;">
      <template #header><strong>📖 期刊介绍</strong></template>
      {{ journal.description }}
    </n-card>

    <div style="margin-bottom: 16px;">
      <template v-if="isLoggedIn">
        <n-button
          v-if="isSubscribed"
          type="error"
          ghost
          :loading="subBusy"
          @click="handleUnsubscribe"
        >
          取消订阅
        </n-button>
        <n-button v-else type="primary" ghost :loading="subBusy" @click="handleSubscribe">
          订阅此期刊
        </n-button>
      </template>
      <n-button
        v-else
        type="primary"
        ghost
        @click="router.push({ path: '/login', query: { redirect: route.fullPath } })"
      >
        登录后订阅
      </n-button>
    </div>

    <n-divider />

    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
      <n-h3 style="margin: 0;">论文列表</n-h3>
      <n-tag v-if="articlesTotal > 0" size="small" :bordered="false">{{ articlesTotal }} 篇</n-tag>
    </div>
    <div v-if="articlesLoading && !articles.length" style="padding: 24px 0; text-align: center;"><n-spin /></div>
    <n-empty
      v-else-if="!articles.length"
      :description="journal.health_status === 'paused' ? '暂无文章（抓取已暂停）' : '暂无文章'"
    />
    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing>
          <template #header>
            <router-link :to="`/articles/${a.id}`" style="text-decoration: none; color: inherit;">
              {{ a.title }}
            </router-link>
          </template>
          <template #description>
            <n-tag v-if="a.content_type === 'preprint'" type="info" size="tiny" :bordered="false" style="margin-right: 6px;">
              预印本
            </n-tag>
            <span style="color: #888; font-size: 13px;">作者：{{ a.authors?.slice(0, 3).join(', ') }}{{ a.authors?.length > 3 ? ' 等' : '' }}</span>
            <br>
            <span style="color: #aaa; font-size: 12px;">{{ a.publish_date || '' }}</span>
            <p
              v-if="a.abstract"
              style="color: #999; font-size: 12px; line-height: 1.6; margin: 6px 0 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
            >
              {{ truncateAbstract(a.abstract) }}
            </p>
          </template>
          <template #footer>
            <router-link :to="`/articles/${a.id}`">查看详情</router-link>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>
    <n-pagination
      v-if="articlesPageCount > 1"
      :page="articlesPage"
      :page-count="articlesPageCount"
      style="margin-top: 16px;"
      @update:page="loadArticlesPage"
    />
  </template>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import {
  subscribeJournal,
  unsubscribeJournal,
  getSubscribedJournals,
} from '@/api/subscriptions'
import { useAuthStore } from '@/stores/auth'
import { truncateAbstract } from '@/utils/abstract'
import { shortUrl } from '@/utils/url'
import {
  NH2, NH3, NButton, NCard, NTag, NDivider, NSpin, NEmpty, NResult,
  NList, NListItem, NThing, NDescriptions, NDescriptionsItem,
  NNumberAnimation, NPagination, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)
const loadError = ref('')
const articlesLoading = ref(false)
const articlesTotal = ref(0)
const articlesPage = ref(1)
const articlesLimit = 20
const articlesPageCount = computed(() => Math.ceil(articlesTotal.value / articlesLimit) || 1)
const isSubscribed = ref(false)
const subBusy = ref(false)

function formatDate(d: string): string {
  return d.slice(0, 10)
}

function dirStatusLabel(s?: string): string {
  const map: Record<string, string> = {
    private: '私有',
    pending_review: '待审公开',
    rejected: '公开未通过',
    hidden: '已下架',
  }
  return map[s || ''] || s || ''
}

function dirStatusType(s?: string): 'default' | 'warning' | 'error' | 'info' {
  if (s === 'pending_review') return 'warning'
  if (s === 'rejected' || s === 'hidden') return 'error'
  if (s === 'private') return 'info'
  return 'default'
}

async function handleSubscribe() {
  if (!journal.value) return
  subBusy.value = true
  try {
    await subscribeJournal(journal.value.id)
    isSubscribed.value = true
    message.success(`已订阅「${journal.value.name}」`)
  } catch (e: any) {
    message.error(e?.message || e?.response?.data?.error || '订阅失败')
  } finally {
    subBusy.value = false
  }
}

async function handleUnsubscribe() {
  if (!journal.value) return
  subBusy.value = true
  try {
    await unsubscribeJournal(journal.value.id)
    isSubscribed.value = false
    message.success('已取消订阅')
  } catch (e: any) {
    message.error(e?.message || '取消失败')
  } finally {
    subBusy.value = false
  }
}

async function loadArticlesPage(p: number) {
  const id = route.params.id as string
  articlesPage.value = p
  articlesLoading.value = true
  try {
    const ar = await getArticles({
      journal_id: id,
      limit: String(articlesLimit),
      offset: String((p - 1) * articlesLimit),
    })
    articles.value = ar.articles
    articlesTotal.value = ar.total ?? ar.articles.length
  } catch (e: any) {
    message.error(e?.message || '加载论文列表失败')
  } finally {
    articlesLoading.value = false
  }
}

onMounted(async () => {
  const id = route.params.id as string
  try {
    const [jr, , subRes] = await Promise.all([
      getJournal(id),
      loadArticlesPage(1),
      auth.isLoggedIn ? getSubscribedJournals().catch(() => null) : Promise.resolve(null),
    ])
    journal.value = jr
    if (jr?.name) document.title = `${jr.name} · Humumu`
    if (subRes) {
      isSubscribed.value = subRes.journals.some((j) => j.id === id)
    }
  } catch (e: any) {
    loadError.value = e?.message || '期刊不存在或无权查看'
  } finally {
    loading.value = false
  }
})
</script>
