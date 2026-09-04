<template>
  <n-button quaternary @click="goBack" style="margin-bottom: 16px;">← 返回</n-button>
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
        {{ contentTypeLabel(article.content_type) }}
      </n-tag>
      <n-tag
        v-if="article.journal_source_type"
        :type="sourceTypeTagType(article.journal_source_type)"
        size="small"
        :bordered="false"
      >
        {{ sourceTypeLabel(article.journal_source_type) }}
      </n-tag>
    </div>

    <n-h2>{{ article.title }}</n-h2>

    <n-descriptions label-placement="left" :column="2" size="small" bordered style="margin-bottom: 16px;">
      <n-descriptions-item label="作者">
        <span :style="authorsLabel ? undefined : 'color:#999'">{{ authorsLabel || '未知' }}</span>
      </n-descriptions-item>
      <n-descriptions-item label="发表日期">
        {{ article.publish_date ? formatDate(article.publish_date) : '未知' }}
      </n-descriptions-item>
      <n-descriptions-item label="DOI">
        <a v-if="article.doi" :href="doiUrl(article.doi)" target="_blank" rel="noopener noreferrer" @click="onOriginalClick">{{ article.doi }}</a>
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
      <n-button
        v-if="article.url"
        type="primary"
        tag="a"
        :href="article.url"
        target="_blank" rel="noopener noreferrer"
        @click="onOriginalClick"
      >
        查看原文
      </n-button>
      <n-button
        v-if="article.doi"
        :type="article.url ? 'default' : 'primary'"
        :quaternary="!!article.url"
        tag="a"
        :href="doiUrl(article.doi)"
        target="_blank" rel="noopener noreferrer"
        @click="onOriginalClick"
      >
        DOI 原文
      </n-button>
      <n-button v-if="article.doi || article.url" quaternary @click="copyLink">
        复制链接
      </n-button>
      <template v-if="isLoggedIn">
        <n-button
          :type="status.is_read ? 'success' : 'default'"
          ghost
          :loading="statusBusy === 'is_read'"
          :disabled="!!statusBusy"
          @click="toggle('is_read')"
        >
          {{ status.is_read ? '已读' : '标为已读' }}
        </n-button>
        <n-button
          :type="status.is_starred ? 'warning' : 'default'"
          ghost
          :loading="statusBusy === 'is_starred'"
          :disabled="!!statusBusy"
          @click="toggle('is_starred')"
        >
          {{ status.is_starred ? '已星标' : '星标' }}
        </n-button>
        <n-button
          :type="status.is_later ? 'info' : 'default'"
          ghost
          :loading="statusBusy === 'is_later'"
          :disabled="!!statusBusy"
          @click="toggle('is_later')"
        >
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
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import { getArticleStatus, updateArticleStatus, recordOriginalClick, type ArticleStatus } from '@/api/reading'
import { useAuthStore } from '@/stores/auth'
import { cleanAbstract } from '@/utils/abstract'
import { shortUrl, doiUrl } from '@/utils/url'
import { formatDate } from '@/utils/datetime'
import { formatAuthors, sourceTypeLabel, sourceTypeTagType, contentTypeLabel } from '@/utils/labels'
import {
  NH2, NH4, NButton, NSpin, NTag, NResult,
  NDescriptions, NDescriptionsItem, useMessage,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const isLoggedIn = computed(() => auth.isLoggedIn)

function goBack() {
  if (window.history.length > 1) router.back()
  else if (article.value?.journal_id) router.push(`/journals/${article.value.journal_id}`)
  else router.push('/')
}

const article = ref<Article | null>(null)
const authorsLabel = computed(() => formatAuthors(article.value?.authors || [], 8))
const loading = ref(true)
const loadError = ref('')
const statusBusy = ref<'is_read' | 'is_starred' | 'is_later' | null>(null)
/** Drop stale detail responses when route id changes mid-flight. */
let articleLoadSeq = 0
const status = ref<ArticleStatus>({
  user_id: '',
  article_id: '',
  is_read: false,
  is_starred: false,
  is_later: false,
  original_clicked_at: null,
})


async function toggle(field: 'is_read' | 'is_starred' | 'is_later') {
  if (!article.value || statusBusy.value) return
  statusBusy.value = field
  try {
    status.value = await updateArticleStatus(article.value.id, { [field]: !status.value[field] })
  } catch (e: any) {
    message.error(e.message || '更新失败')
  } finally {
    statusBusy.value = null
  }
}

let originalClickBusy = false

async function onOriginalClick() {
  if (!isLoggedIn.value || !article.value || originalClickBusy) return
  originalClickBusy = true
  try {
    await recordOriginalClick(article.value.id)
    if (!status.value.is_read) {
      status.value = await updateArticleStatus(article.value.id, { is_read: true })
    }
  } catch {
    // non-blocking
  } finally {
    originalClickBusy = false
  }
}

async function copyLink() {
  if (!article.value) return
  const link = article.value.doi
    ? doiUrl(article.value.doi)
    : article.value.url || ''
  if (!link) return
  // Same side-effect as opening DOI/原文: record click + mark read when logged in.
  await onOriginalClick()
  try {
    await navigator.clipboard.writeText(link)
    message.success('链接已复制')
  } catch {
    message.error('复制失败，请手动选择链接')
  }
}

async function loadArticle(id: string) {
  const seq = ++articleLoadSeq
  loading.value = true
  loadError.value = ''
  article.value = null
  status.value = {
    user_id: '',
    article_id: '',
    is_read: false,
    is_starred: false,
    is_later: false,
    original_clicked_at: null,
  }
  try {
    const next = await getArticle(id)
    if (seq !== articleLoadSeq) return
    article.value = next
    if (article.value?.title) {
      const short =
        article.value.title.length > 48
          ? `${article.value.title.slice(0, 48)}…`
          : article.value.title
      document.title = `${short} · Humumu`
    }
    if (isLoggedIn.value) {
      try {
        const st = await getArticleStatus(id)
        if (seq !== articleLoadSeq) return
        status.value = st
        if (!status.value.is_read) {
          const updated = await updateArticleStatus(id, { is_read: true })
          if (seq !== articleLoadSeq) return
          status.value = updated
        }
      } catch {
        // status optional
      }
    }
  } catch (e: any) {
    if (seq !== articleLoadSeq) return
    loadError.value = e?.message || '文章不存在或无权查看'
  } finally {
    if (seq === articleLoadSeq) loading.value = false
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string' && id) loadArticle(id)
  },
)

onMounted(() => {
  const id = route.params.id as string
  if (id) loadArticle(id)
})
</script>
