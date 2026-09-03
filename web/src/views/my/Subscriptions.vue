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
          <n-thing :title="j.name">
            <template #description>
              <n-space size="small" style="margin-top: 4px;">
                <n-tag size="tiny" :bordered="false">{{ j.source_type }}</n-tag>
                <n-tag v-if="j.content_type === 'preprint'" size="tiny" type="info" :bordered="false">预印本</n-tag>
                <n-tag size="tiny" type="warning" :bordered="false">{{ freqLabel(j.push_frequency) }}</n-tag>
              </n-space>
            </template>
          </n-thing>
          <template #suffix>
            <n-space>
              <n-button size="small" ghost @click="openPrefs(j)">推送设置</n-button>
              <n-button size="small" type="error" ghost @click="unsubscribe(j.id)">取消关注</n-button>
            </n-space>
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

  <!-- Per-subscription prefs -->
  <n-modal v-model:show="showPrefsModal">
    <n-card style="width: 420px;" :title="prefsJournal ? `推送设置 · ${prefsJournal.name}` : '推送设置'" role="dialog">
      <n-form>
        <n-form-item label="推送频率">
          <n-radio-group v-model:value="prefsForm.push_frequency">
            <n-radio value="default">跟随全局</n-radio>
            <n-radio value="realtime">实时</n-radio>
            <n-radio value="daily">每日汇总</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="渠道">
          <n-space>
            <n-checkbox v-model:checked="prefsForm.email_enabled">Email</n-checkbox>
            <n-checkbox v-model:checked="prefsForm.wechat_enabled">微信</n-checkbox>
          </n-space>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showPrefsModal = false">取消</n-button>
        <n-button type="primary" :loading="prefsSaving" @click="savePrefs">保存</n-button>
      </template>
    </n-card>
  </n-modal>

  <!-- Add RSS Modal -->
  <n-modal v-model:show="showAddModal" @update:show="onModalShow">
    <n-card style="width: 480px;" title="添加 RSS 订阅" role="dialog">
      <div v-if="addStep === 'url'">
        <n-form>
          <n-form-item label="RSS 链接">
            <n-input v-model:value="addUrl" placeholder="https://rss.arxiv.org/rss/cs.AI" @keyup.enter="handlePreview" />
          </n-form-item>
        </n-form>
      </div>

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
          <n-form-item label="可见性">
            <n-radio-group v-model:value="addVisibility">
              <n-radio value="private">仅自己使用</n-radio>
              <n-radio value="apply_public">申请公开</n-radio>
            </n-radio-group>
          </n-form-item>
        </n-form>
        <n-list v-if="addPreviewItems.length" style="margin-top: 8px;">
          <n-list-item v-for="(it, idx) in addPreviewItems.slice(0, 5)" :key="idx">
            <n-thing :title="it.title || '(无标题)'" :description="it.published || it.url" />
          </n-list-item>
        </n-list>
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

      <n-alert v-if="addError" type="error" :title="addError" closable @close="addError = ''" style="margin-top: 12px;" />
    </n-card>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  getSubscribedJournals,
  unsubscribeJournal,
  updateJournalSubscriptionPrefs,
  getAuthors,
  addAuthor as addAuthorApi,
  removeAuthor as removeAuthorApi,
  getKeywords,
  addKeyword as addKeywordApi,
  removeKeyword as removeKeywordApi,
  type SubscribedJournal,
  type AuthorTracking,
  type KeywordSubscription,
} from '@/api/subscriptions'
import { previewJournal, addMyJournal, type PreviewItem } from '@/api/journals'
import {
  NH2, NButton, NTabs, NTabPane, NSpin, NEmpty, NList, NListItem, NThing, NInput, NTag,
  NModal, NCard, NForm, NFormItem, NAlert, NSpace, NRadio, NRadioGroup, NCheckbox,
} from 'naive-ui'

const message = useMessage()
const activeTab = ref('journals')

const journals = ref<SubscribedJournal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])

const newAuthor = ref('')
const newKeyword = ref('')

const showPrefsModal = ref(false)
const prefsJournal = ref<SubscribedJournal | null>(null)
const prefsSaving = ref(false)
const prefsForm = ref({
  push_frequency: 'default',
  email_enabled: true,
  wechat_enabled: true,
})

const showAddModal = ref(false)
const addStep = ref<'url' | 'confirm'>('url')
const addUrl = ref('')
const addName = ref('')
const addSourceType = ref('')
const addVisibility = ref<'private' | 'apply_public'>('private')
const addPreviewItems = ref<PreviewItem[]>([])
const addError = ref('')
const previewLoading = ref(false)
const addLoading = ref(false)

function freqLabel(f?: string): string {
  if (f === 'realtime') return '实时'
  if (f === 'daily') return '每日'
  return '跟随全局'
}

function resetAddModal() {
  addStep.value = 'url'
  addUrl.value = ''
  addName.value = ''
  addSourceType.value = ''
  addVisibility.value = 'private'
  addPreviewItems.value = []
  addError.value = ''
}

function onModalShow(show: boolean) {
  if (!show) resetAddModal()
}

function openPrefs(j: SubscribedJournal) {
  prefsJournal.value = j
  prefsForm.value = {
    push_frequency: j.push_frequency || 'default',
    email_enabled: j.email_enabled !== false,
    wechat_enabled: j.wechat_enabled !== false,
  }
  showPrefsModal.value = true
}

async function savePrefs() {
  if (!prefsJournal.value) return
  prefsSaving.value = true
  try {
    const updated = await updateJournalSubscriptionPrefs(prefsJournal.value.id, {
      push_frequency: prefsForm.value.push_frequency,
      email_enabled: prefsForm.value.email_enabled,
      wechat_enabled: prefsForm.value.wechat_enabled,
    })
    const j = journals.value.find(x => x.id === prefsJournal.value!.id)
    if (j) {
      j.push_frequency = updated.push_frequency
      j.email_enabled = updated.email_enabled
      j.wechat_enabled = updated.wechat_enabled
    }
    message.success('推送设置已保存')
    showPrefsModal.value = false
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    prefsSaving.value = false
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
    authors.value = (await getAuthors()).authors
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
    keywords.value = (await getKeywords()).keywords
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
    addPreviewItems.value = result.items || []
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
    const result = await addMyJournal(addName.value.trim(), addUrl.value.trim(), addVisibility.value)
    if (result.already_existed) {
      message.success(`已关注已有期刊「${result.journal.name}」`)
    } else if (addVisibility.value === 'apply_public') {
      message.success(`已添加「${result.journal.name}」，公开申请已提交审核`)
    } else {
      message.success(`已添加并关注「${result.journal.name}」（私有）`)
    }
    showAddModal.value = false
    resetAddModal()
    journals.value = (await getSubscribedJournals()).journals
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
