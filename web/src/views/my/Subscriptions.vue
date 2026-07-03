<template>
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <n-h2 style="margin: 0;">订阅管理</n-h2>
    <n-button type="primary" secondary @click="showAddModal = true">添加 RSS</n-button>
  </div>

  <n-tabs v-model:value="activeTab" style="margin-top: 16px;">
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

  <!-- Add RSS Modal -->
  <n-modal v-model:show="showAddModal" @update:show="onModalShow">
    <n-card style="width: 480px;" title="添加 RSS 订阅" role="dialog">
      <!-- Step 1: URL input -->
      <div v-if="addStep === 'url'">
        <n-form>
          <n-form-item label="RSS 链接">
            <n-input v-model:value="addUrl" placeholder="https://rss.cnki.net/knavi/rss/GLSJ?pcode=CJFD,CCJD" @keyup.enter="handlePreview" />
          </n-form-item>
        </n-form>
      </div>

      <!-- Step 2: Confirm info -->
      <div v-else-if="addStep === 'confirm'">
        <n-form>
          <n-form-item label="RSS 链接">
            <n-input :value="addUrl" disabled />
          </n-form-item>
          <n-form-item label="期刊名称">
            <n-input v-model:value="addName" @keyup.enter="handleAdd" />
          </n-form-item>
          <n-form-item label="类型">
            <n-input :value="addSourceType" disabled />
          </n-form-item>
        </n-form>
      </div>

      <template #footer>
        <template v-if="addStep === 'url'">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="handlePreview" :loading="previewLoading" :disabled="!addUrl.trim()">
            预览
          </n-button>
        </template>
        <template v-else>
          <n-button @click="addStep = 'url'">返回</n-button>
          <n-button type="primary" @click="handleAdd" :loading="addLoading">添加并关注</n-button>
        </template>
      </template>

      <!-- Error -->
      <n-alert v-if="addError" type="error" :title="addError" closable @close="addError = ''" style="margin-top: 12px;" />
    </n-card>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { getSubscribedJournals, unsubscribeJournal, getAuthors, addAuthor as addAuthorApi, removeAuthor as removeAuthorApi, getKeywords, addKeyword as addKeywordApi, removeKeyword as removeKeywordApi } from '@/api/subscriptions'
import { previewJournal, addMyJournal } from '@/api/journals'
import { NH2, NButton, NTabs, NTabPane, NSpin, NEmpty, NList, NListItem, NThing, NInput, NTag, NModal, NCard, NForm, NFormItem, NAlert } from 'naive-ui'
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

// Add RSS modal state
const showAddModal = ref(false)
const addStep = ref<'url' | 'confirm'>('url')
const addUrl = ref('')
const addName = ref('')
const addSourceType = ref('')
const addError = ref('')
const previewLoading = ref(false)
const addLoading = ref(false)

function resetAddModal() {
  addStep.value = 'url'
  addUrl.value = ''
  addName.value = ''
  addSourceType.value = ''
  addError.value = ''
}

function onModalShow(show: boolean) {
  if (!show) {
    resetAddModal()
  }
}

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

async function handlePreview() {
  previewLoading.value = true
  addError.value = ''
  try {
    const result = await previewJournal(addUrl.value.trim())
    addName.value = result.name
    addSourceType.value = result.source_type
    addStep.value = 'confirm'
  } catch (e: any) {
    addError.value = e.message || '无法获取 feed 信息，请检查链接是否正确'
  } finally {
    previewLoading.value = false
  }
}

async function handleAdd() {
  addLoading.value = true
  addError.value = ''
  try {
    const result = await addMyJournal(addName.value.trim(), addUrl.value.trim())
    if (result.already_existed) {
      message.success(`已关注已有期刊「${result.journal.name}」`)
    } else {
      message.success(`已添加并关注「${result.journal.name}」`)
    }
    showAddModal.value = false
    addStep.value = 'url'
    addUrl.value = ''
    addName.value = ''
    addSourceType.value = ''
    // Refresh subscribed journals list
    const res = await getSubscribedJournals()
    journals.value = res.journals
  } catch (e: any) {
    addError.value = e.message || '添加失败'
  } finally {
    addLoading.value = false
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
