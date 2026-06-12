<template>
  <n-h2>订阅管理</n-h2>
  <n-tabs v-model:value="activeTab">
    <n-tab-pane name="journals" tab="期刊">
      <div v-if="loadingJournals"><n-spin /></div>
      <n-empty v-else-if="!journals.length" description="尚未关注任何期刊" />
      <n-list v-else>
        <n-list-item v-for="j in journals" :key="j.id">
          <n-thing :title="j.name" :description="j.source_type" />
          <template #suffix>
            <n-button size="small" type="error" ghost @click="unsubscribe(j.id)">取消关注</n-button>
          </template>
        </n-list-item>
      </n-list>
    </n-tab-pane>

    <n-tab-pane name="authors" tab="作者">
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <n-input v-model:value="newAuthor" placeholder="作者姓名" />
        <n-button @click="addAuthor" :disabled="!newAuthor.trim()">添加</n-button>
      </div>
      <n-empty v-if="!authors.length" description="尚未追踪任何作者" />
      <n-tag v-for="a in authors" :key="a.id" closable @close="removeAuthor(a.id)" style="margin: 4px;">
        {{ a.author_name }}
      </n-tag>
    </n-tab-pane>

    <n-tab-pane name="keywords" tab="关键词">
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <n-input v-model:value="newKeyword" placeholder="关键词" />
        <n-button @click="addKeyword" :disabled="!newKeyword.trim()">添加</n-button>
      </div>
      <n-empty v-if="!keywords.length" description="尚未订阅任何关键词" />
      <n-tag v-for="k in keywords" :key="k.id" closable @close="removeKeyword(k.id)" style="margin: 4px;">
        {{ k.keyword }}
      </n-tag>
    </n-tab-pane>
  </n-tabs>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { getSubscribedJournals, unsubscribeJournal, getAuthors, addAuthor as addAuthorApi, removeAuthor as removeAuthorApi, getKeywords, addKeyword as addKeywordApi, removeKeyword as removeKeywordApi } from '@/api/subscriptions'
import { NH2, NTabs, NTabPane, NSpin, NEmpty, NList, NListItem, NThing, NButton, NInput, NTag } from 'naive-ui'
import type { Journal } from '@/api/journals'
import type { AuthorTracking, KeywordSubscription } from '@/api/subscriptions'

const message = useMessage()
const activeTab = ref('journals')

const journals = ref<Journal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])

const newAuthor = ref('')
const newKeyword = ref('')

async function unsubscribe(id: string) {
  try {
    await unsubscribeJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
    message.success('已取消关注')
  } catch (e: any) {
    message.error(e.message)
  }
}

async function addAuthor() {
  try {
    await addAuthorApi(newAuthor.value.trim())
    newAuthor.value = ''
    const res = await getAuthors()
    authors.value = res.authors
    message.success('已添加')
  } catch (e: any) {
    message.error(e.message)
  }
}

async function removeAuthor(id: string) {
  try {
    await removeAuthorApi(id)
    authors.value = authors.value.filter(a => a.id !== id)
  } catch (e: any) {
    message.error(e.message)
  }
}

async function addKeyword() {
  try {
    await addKeywordApi(newKeyword.value.trim())
    newKeyword.value = ''
    const res = await getKeywords()
    keywords.value = res.keywords
    message.success('已添加')
  } catch (e: any) {
    message.error(e.message)
  }
}

async function removeKeyword(id: string) {
  try {
    await removeKeywordApi(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
  } catch (e: any) {
    message.error(e.message)
  }
}

onMounted(async () => {
  try {
    journals.value = (await getSubscribedJournals()).journals
    authors.value = (await getAuthors()).authors
    keywords.value = (await getKeywords()).keywords
  } finally {
    loadingJournals.value = false
  }
})
</script>
