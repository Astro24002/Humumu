<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <div v-if="loading"><n-spin /></div>
  <n-result v-else-if="loadError" status="404" :title="loadError" description="可能是私有源或已删除">
    <template #footer>
      <n-button @click="router.push('/')">回广场</n-button>
      <n-button type="primary" style="margin-left: 8px;" @click="router.push('/my')">我的更新</n-button>
    </template>
  </n-result>
  <template v-else-if="article">
    <div style="margin-bottom: 12px;">
      <router-link v-if="article.journal_name" :to="`/journals/${article.journal_id}`" style="text-decoration: none;">
        <n-tag :bordered="false" style="margin-right: 6px;">{{ article.journal_name }}</n-tag>
      </router-link>
      <n-tag v-if="article.content_type === 'preprint'" type="info" size="small" :bordered="false" style="margin-right: 6px;">
        预印本
      </n-tag>
      <n-tag :type="article.journal_source_type === 'arxiv' ? 'info' : 'success'" size="small" :bordered="false">
        {{ article.journal_source_type }}
      </n-tag>
    </div>

    <n-h2>{{ article.title }}</n-h2>

    <n-descriptions label-placement="left" :column="2" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="作者">
        {{ article.authors?.join(', ') || '未知' }}
      </n-descriptions-item>
      <n-descriptions-item label="发表日期">
        {{ article.publish_date || '未知' }}
      </n-descriptions-item>
      <n-descriptions-item label="DOI">
        <a v-if="article.doi" :href="doiUrl(article.doi)" target="_blank">{{ article.doi }}</a>
        <span v-else>-</span>
      </n-descriptions-item>
      <n-descriptions-item label="原文链接">
        <a v-if="article.url" :href="article.url" target="_blank" rel="noopener noreferrer" @click="onOriginalClick">{{ shortUrl(article.url) }}</a>
        <span v-else>-</span>
      </n-descriptions-item>
      <n-descriptions-item label="抓取时间">
        {{ formatDate(article.fetched_at) }}
      </n-descriptions-item>
    </n-descriptions>

    <n-h4>摘要</n-h4>
    <p v-if="cleanAbstract(article.abstract)" style="line-height: 1.8; white-space: pre-wrap;">{{ cleanAbstract(article.abstract) }}</p>
    <p v-else style="color: #999; line-height: 1.8;">暂无摘要</p>

    <div style="margin-top: 20px; display: flex; flex-wrap: wrap; gap: 12px;">
      <n-button type="primary" tag="a" :href="article.url" target="_blank" @click="onOriginalClick">
        查看原文
      </n-button>
      <n-button v-if="article.doi" quaternary tag="a" :href="doiUrl(article.doi)" target="_blank" @click="onOriginalClick">
        DOI 原文
      </n-button>
      <n-button v-if="article.doi || article.url" quaternary @click="copyLink">
        复制链接
      </n-button>
      <template v-if="isLoggedIn">
        <n-button :type="status.is_read ? 'success' : 'default'" ghost @click="toggle('is_read')" :loading="statusSaving">
          {{ status.is_read ? '已读' : '标为已读' }}
        </n-button>
        <n-button :type="status.is_starred ? 'warning' : 'default'" ghost @click="toggle('is_starred')" :loading="statusSaving">
          {{ status.is_starred ? '已星标' : '星标' }}
        </n-button>
        <n-button :type="status.is_later ? 'info' : 'default'" ghost @click="toggle('is_later')" :loading="statusSaving">
          {{ status.is_later ? '稍后再看中' : '稍后再看' }}
        </n-button>
      </template>
      <n-button
        v-else
        ghost
        @click="router.push({ path: '/login', query: { redirect: route.fullPath } })"
      >
        登录后管理阅读状态
      </n-button>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import { getArticleStatus, updateArticleStatus, recordOriginalClick, type ArticleStatus } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { cleanAbstract } from '@/utils/abstract'
import {
  NH2, NH4, NButton, NSpin, NTag, NResult,
  NDescriptions, NDescriptionsItem, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)
const article = ref<Article | null>(null)
const loading = ref(true)
const loadError = ref('')
const statusSaving = ref(false)
const status = ref<ArticleStatus>({
  user_id: '',
  article_id: '',
  is_read: false,
  is_starred: false,
  is_later: false,
  original_clicked_at: null,
})

function doiUrl(doi: string): string {
  if (doi.startsWith('http')) return doi
  return `https://doi.org/${doi}`
}

function formatDate(d: string): string {
  return d.slice(0, 10)
}

function shortUrl(url: string): string {
  if (!url) return ''
  try {
    const u = new URL(url)
    const path = u.pathname === '/' ? '' : u.pathname
    const full = `${u.host}${path}`
    return full.length > 48 ? `${full.slice(0, 48)}…` : full
  } catch {
    return url.length > 48 ? `${url.slice(0, 48)}…` : url
  }
}

async function toggle(field: 'is_read' | 'is_starred' | 'is_later') {
  if (!article.value) return
  statusSaving.value = true
  try {
    status.value = await updateArticleStatus(article.value.id, { [field]: !status.value[field] })
  } catch (e: any) {
    message.error(e.message || '更新失败')
  } finally {
    statusSaving.value = false
  }
}

async function onOriginalClick() {
  if (!isLoggedIn.value || !article.value) return
  try {
    await recordOriginalClick(article.value.id)
    if (!status.value.is_read) {
      status.value = await updateArticleStatus(article.value.id, { is_read: true })
    }
  } catch {
    // non-blocking
  }
}

async function copyLink() {
  if (!article.value) return
  const link = article.value.doi
    ? doiUrl(article.value.doi)
    : article.value.url || ''
  if (!link) return
  try {
    await navigator.clipboard.writeText(link)
    message.success('链接已复制')
  } catch {
    message.error('复制失败，请手动选择链接')
  }
}

onMounted(async () => {
  const id = route.params.id as string
  try {
    article.value = await getArticle(id)
    if (article.value?.title) {
      const short =
        article.value.title.length > 48
          ? `${article.value.title.slice(0, 48)}…`
          : article.value.title
      document.title = `${short} · Humumu`
    }
    if (isLoggedIn.value) {
      try {
        status.value = await getArticleStatus(id)
        if (!status.value.is_read) {
          status.value = await updateArticleStatus(id, { is_read: true })
        }
      } catch {
        // status optional
      }
    }
  } catch (e: any) {
    loadError.value = e?.message || '文章不存在或无权查看'
  } finally {
    loading.value = false
  }
})
</script>
