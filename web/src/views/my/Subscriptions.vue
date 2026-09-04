<template>
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
    <n-h2 style="margin: 0;">订阅管理</n-h2>
    <n-space>
      <n-button size="small" :loading="loadingJournals && !!journals.length" @click="reloadAll">刷新</n-button>
      <n-button type="primary" secondary @click="showAddModal = true">添加 RSS</n-button>
    </n-space>
  </div>

  <n-tabs v-model:value="activeTab" style="margin-top: 16px;" @update:value="onTabChange">
    <n-tab-pane name="journals" :tab="journalsTabLabel">
      <div v-if="loadingJournals"><n-spin /></div>
      <n-empty v-else-if="!journals.length" description="尚未关注任何期刊">
        <template #extra>
          <n-button @click="router.push('/journals')">浏览期刊广场</n-button>
        </template>
      </n-empty>
      <n-list v-else>
        <n-list-item v-for="j in journals" :key="j.id">
          <n-thing>
            <template #header>
              <router-link :to="`/journals/${j.id}`" style="color: inherit; text-decoration: none;">
                {{ j.name }}
              </router-link>
            </template>
            <template #description>
              <n-space size="small" style="margin-top: 4px;">
                <n-tag size="tiny" :type="sourceTypeTagType(j.source_type)" :bordered="false">{{ sourceTypeLabel(j.source_type) }}</n-tag>
                <n-tag v-if="j.content_type === 'preprint'" size="tiny" type="info" :bordered="false">{{ contentTypeLabel(j.content_type) }}</n-tag>
                <n-tag
                  v-if="j.directory_status && j.directory_status !== 'public'"
                  size="tiny"
                  :type="dirStatusType(j.directory_status)"
                  :bordered="false"
                >
                  {{ dirStatusLabel(j.directory_status) }}
                </n-tag>
                <n-tag
                  v-if="j.health_status === 'paused'"
                  size="tiny"
                  type="error"
                  :bordered="false"
                  :title="j.last_error || '抓取已暂停'"
                >
                  {{ healthStatusLabel(j.health_status) }}
                </n-tag>
                <n-tag size="tiny" type="warning" :bordered="false">{{ freqLabel(j.push_frequency) }}</n-tag>
                <n-tag v-if="j.email_enabled !== false" size="tiny" :type="channelTagType('email')" :bordered="false">{{ channelLabel('email') }}</n-tag>
                <n-tag v-if="j.wechat_enabled !== false" size="tiny" :type="channelTagType('wechat')" :bordered="false">{{ channelLabel('wechat') }}</n-tag>
              </n-space>
            </template>
          </n-thing>
          <template #suffix>
            <n-space>
              <n-button size="small" ghost :disabled="unsubBusyId === j.id" @click="openPrefs(j)">推送设置</n-button>
              <n-button size="small" type="error" ghost :loading="unsubBusyId === j.id" :disabled="unsubBusyId === j.id" @click="confirmUnsubscribe(j)">取消关注</n-button>
            </n-space>
          </template>
        </n-list-item>
      </n-list>
    </n-tab-pane>

    <n-tab-pane name="authors" :tab="authorsTabLabel">
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <n-input
          v-model:value="newAuthor"
          placeholder="作者姓名"
          :disabled="authorBusy"
          @keyup.enter="addAuthor"
        />
        <n-button @click="addAuthor" :loading="authorBusy" :disabled="!newAuthor.trim() || authorBusy">添加</n-button>
      </div>
      <n-empty v-if="!authors.length" description="尚未追踪任何作者">
        <template #extra>
          <span style="color: #888; font-size: 13px;">在上方输入作者姓名后点击添加</span>
        </template>
      </n-empty>
      <n-tag
        v-for="a in authors"
        :key="a.id"
        :closable="removeBusyId !== a.id"
        :disabled="removeBusyId === a.id"
        @close="confirmRemoveAuthor(a)"
        style="margin: 4px;"
      >
        {{ a.author_name }}
      </n-tag>
    </n-tab-pane>

    <n-tab-pane name="keywords" :tab="keywordsTabLabel">
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <n-input
          v-model:value="newKeyword"
          placeholder="关键词"
          :disabled="keywordBusy"
          @keyup.enter="addKeyword"
        />
        <n-button @click="addKeyword" :loading="keywordBusy" :disabled="!newKeyword.trim() || keywordBusy">添加</n-button>
      </div>
      <n-empty v-if="!keywords.length" description="尚未订阅任何关键词">
        <template #extra>
          <span style="color: #888; font-size: 13px;">在上方输入关键词后点击添加</span>
        </template>
      </n-empty>
      <n-tag
        v-for="k in keywords"
        :key="k.id"
        :closable="removeBusyId !== k.id"
        :disabled="removeBusyId === k.id"
        @close="confirmRemoveKeyword(k)"
        style="margin: 4px;"
      >
        {{ k.keyword }}
      </n-tag>
    </n-tab-pane>
  </n-tabs>

  <!-- Per-subscription prefs -->
  <n-modal
    v-model:show="showPrefsModal"
    :mask-closable="!prefsSaving"
    :close-on-esc="!prefsSaving"
    @update:show="onPrefsModalShow"
  >
    <n-card style="width: 420px;" :title="prefsJournal ? `推送设置 · ${prefsJournal.name}` : '推送设置'" role="dialog">
      <n-form :disabled="prefsSaving">
        <n-form-item label="推送频率">
          <n-radio-group v-model:value="prefsForm.push_frequency">
            <n-radio value="default">{{ freqLabel('default') }}</n-radio>
            <n-radio value="realtime">{{ freqLabel('realtime') }}</n-radio>
            <n-radio value="daily">{{ freqLabel('daily') }}</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="渠道">
          <n-space>
            <n-checkbox v-model:checked="prefsForm.email_enabled">{{ channelLabel('email') }}</n-checkbox>
            <n-checkbox v-model:checked="prefsForm.wechat_enabled">{{ channelLabel('wechat') }}</n-checkbox>
          </n-space>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button :disabled="prefsSaving" @click="showPrefsModal = false">取消</n-button>
        <n-button type="primary" :loading="prefsSaving" :disabled="prefsSaving" @click="savePrefs">保存</n-button>
      </template>
    </n-card>
  </n-modal>

  <!-- Add RSS Modal -->
  <n-modal
    v-model:show="showAddModal"
    :mask-closable="!(previewLoading || addLoading)"
    :close-on-esc="!(previewLoading || addLoading)"
    @update:show="onModalShow"
  >
    <n-card style="width: 480px;" title="添加 RSS 订阅" role="dialog">
      <div v-if="addStep === 'url'">
        <n-form>
          <n-form-item label="RSS 链接">
            <n-input
              v-model:value="addUrl"
              placeholder="https://rss.arxiv.org/rss/cs.AI"
              :disabled="previewLoading"
              @keyup.enter="handlePreview"
            />
          </n-form-item>
        </n-form>
      </div>

      <div v-else-if="addStep === 'confirm'">
        <n-form>
          <n-form-item label="RSS 链接">
            <n-input :value="addUrl" disabled />
          </n-form-item>
          <n-form-item label="期刊名称">
            <n-input v-model:value="addName" :disabled="addLoading" @keyup.enter="handleAdd" />
          </n-form-item>
          <n-form-item label="类型">
            <n-input :value="sourceTypeLabel(addSourceType) || addSourceType" disabled />
          </n-form-item>
          <n-form-item label="可见性">
            <n-radio-group v-model:value="addVisibility" :disabled="addLoading">
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
          <n-button :disabled="previewLoading" @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="handlePreview" :loading="previewLoading" :disabled="!addUrl.trim() || previewLoading">
            预览
          </n-button>
        </template>
        <template v-else>
          <n-button :disabled="addLoading" @click="addStep = 'url'">返回</n-button>
          <n-button type="primary" @click="handleAdd" :loading="addLoading" :disabled="addLoading || !addName.trim()">添加并关注</n-button>
        </template>
      </template>

      <n-alert v-if="addError" type="error" :title="addError" closable @close="addError = ''" style="margin-top: 12px;" />
    </n-card>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
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
import { dirStatusLabel, dirStatusType, freqLabel, sourceTypeLabel, sourceTypeTagType, contentTypeLabel, healthStatusLabel, channelLabel, channelTagType } from '@/utils/labels'
import {
  NH2, NButton, NTabs, NTabPane, NSpin, NEmpty, NList, NListItem, NThing, NInput, NTag,
  NModal, NCard, NForm, NFormItem, NAlert, NSpace, NRadio, NRadioGroup, NCheckbox,
} from 'naive-ui'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const TAB_VALUES = new Set(['journals', 'authors', 'keywords'])
const activeTab = ref('journals')
/** Skip one route→state write when we just pushed query ourselves. */
let suppressTabQueryApply = false

function tabFromQuery(): string {
  const raw = route.query.tab
  return typeof raw === 'string' && TAB_VALUES.has(raw) ? raw : 'journals'
}

function applyTabFromQuery() {
  activeTab.value = tabFromQuery()
}

function syncTabToQuery() {
  const next: Record<string, string> = {}
  if (activeTab.value && activeTab.value !== 'journals') next.tab = activeTab.value
  const cur = route.query
  const same = (cur.tab || undefined) === next.tab
  if (same) return
  suppressTabQueryApply = true
  router.replace({ query: next })
}

const journals = ref<SubscribedJournal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])

const journalsTabLabel = computed(() =>
  journals.value.length ? `期刊 (${journals.value.length})` : '期刊',
)
const authorsTabLabel = computed(() =>
  authors.value.length ? `作者 (${authors.value.length})` : '作者',
)
const keywordsTabLabel = computed(() =>
  keywords.value.length ? `关键词 (${keywords.value.length})` : '关键词',
)

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
const unsubBusyId = ref<string | null>(null)
const authorBusy = ref(false)
const keywordBusy = ref(false)
const removeBusyId = ref<string | null>(null)
/** Drop stale subscription bundle responses when reload races mid-flight. */
let subsLoadSeq = 0




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
  // Keep the dialog open while preview/add is in flight (escape / mask click).
  if (!show && (previewLoading.value || addLoading.value)) {
    showAddModal.value = true
    return
  }
  if (!show) resetAddModal()
}

function onPrefsModalShow(show: boolean) {
  if (!show && prefsSaving.value) {
    showPrefsModal.value = true
  }
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
  if (!prefsJournal.value || prefsSaving.value) return
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

function confirmUnsubscribe(j: { id: string; name: string }) {
  dialog.warning({
    title: '取消关注',
    content: `确认取消关注「${j.name}」？`,
    positiveText: '取消关注',
    negativeText: '保留',
    onPositiveClick: () => unsubscribe(j.id),
  })
}

async function unsubscribe(id: string) {
  if (unsubBusyId.value === id) return
  unsubBusyId.value = id
  try {
    await unsubscribeJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
    message.success('已取消关注')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    unsubBusyId.value = null
  }
}

async function addAuthor() {
  const name = newAuthor.value.trim()
  if (!name || authorBusy.value) return
  authorBusy.value = true
  try {
    await addAuthorApi(name)
    newAuthor.value = ''
    authors.value = (await getAuthors()).authors
    message.success('已添加')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    authorBusy.value = false
  }
}

function confirmRemoveAuthor(a: { id: string; author_name: string }) {
  dialog.warning({
    title: '移除作者',
    content: `确认停止追踪「${a.author_name}」？`,
    positiveText: '移除',
    negativeText: '返回',
    onPositiveClick: () => removeAuthor(a.id),
  })
}

async function removeAuthor(id: string) {
  if (removeBusyId.value === id) return
  removeBusyId.value = id
  try {
    await removeAuthorApi(id)
    authors.value = authors.value.filter(a => a.id !== id)
    message.success('已移除作者')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    removeBusyId.value = null
  }
}

async function addKeyword() {
  const kw = newKeyword.value.trim()
  if (!kw || keywordBusy.value) return
  keywordBusy.value = true
  try {
    await addKeywordApi(kw)
    newKeyword.value = ''
    keywords.value = (await getKeywords()).keywords
    message.success('已添加')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    keywordBusy.value = false
  }
}

function confirmRemoveKeyword(k: { id: string; keyword: string }) {
  dialog.warning({
    title: '移除关键词',
    content: `确认取消关键词「${k.keyword}」？`,
    positiveText: '移除',
    negativeText: '返回',
    onPositiveClick: () => removeKeyword(k.id),
  })
}

async function removeKeyword(id: string) {
  if (removeBusyId.value === id) return
  removeBusyId.value = id
  try {
    await removeKeywordApi(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
    message.success('已移除关键词')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    removeBusyId.value = null
  }
}

async function handlePreview() {
  if (previewLoading.value) return
  const url = addUrl.value.trim()
  if (!url) return
  previewLoading.value = true
  addError.value = ''
  try {
    const result = await previewJournal(url)
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
  if (addLoading.value) return
  const name = addName.value.trim()
  if (!name) {
    addError.value = '请填写期刊名称'
    return
  }
  addLoading.value = true
  addError.value = ''
  try {
    const result = await addMyJournal(name, addUrl.value.trim(), addVisibility.value)
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

async function reloadAll() {
  const seq = ++subsLoadSeq
  loadingJournals.value = true
  try {
    const [jRes, aRes, kRes] = await Promise.all([
      getSubscribedJournals(),
      getAuthors(),
      getKeywords(),
    ])
    if (seq !== subsLoadSeq) return
    journals.value = jRes.journals
    authors.value = aRes.authors
    keywords.value = kRes.keywords
  } catch (e: any) {
    if (seq !== subsLoadSeq) return
    message.error(e?.message || '加载订阅失败')
  } finally {
    if (seq === subsLoadSeq) loadingJournals.value = false
  }
}

function onTabChange(name: string) {
  activeTab.value = TAB_VALUES.has(name) ? name : 'journals'
  syncTabToQuery()
}

watch(
  () => route.query.tab,
  () => {
    if (suppressTabQueryApply) {
      suppressTabQueryApply = false
      return
    }
    applyTabFromQuery()
  },
)

onMounted(() => {
  applyTabFromQuery()
  reloadAll()
})
</script>
