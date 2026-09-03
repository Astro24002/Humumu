<template>
  <view class="container">
    <view v-if="!auth.isLoggedIn" class="login-prompt">
      <text>登录后可管理订阅</text>
      <button @click="goLogin" class="btn-login">去登录</button>
    </view>

    <template v-else>
      <view class="tabs">
        <text :class="['tab', tab === 'journals' && 'active']" @click="tab='journals'">期刊</text>
        <text :class="['tab', tab === 'authors' && 'active']" @click="tab='authors'">作者</text>
        <text :class="['tab', tab === 'keywords' && 'active']" @click="tab='keywords'">关键词</text>
      </view>

      <view v-if="tab === 'journals'">
        <view class="add-feed">
          <input v-model="feedUrl" placeholder="粘贴 RSS/Atom URL" class="add-input" />
          <input v-model="feedName" placeholder="名称（可选，预览后自动填充）" class="add-input" />
          <view class="add-feed-row">
            <label class="vis-opt" @click="feedVisibility = 'private'">
              <text :class="['radio', feedVisibility === 'private' && 'on']" />
              <text>私有</text>
            </label>
            <label class="vis-opt" @click="feedVisibility = 'apply_public'">
              <text :class="['radio', feedVisibility === 'apply_public' && 'on']" />
              <text>申请公开</text>
            </label>
            <button class="btn-add" size="mini" :loading="addingFeed" @click="addFeed">添加源</button>
          </view>
          <view v-if="previewItems.length" class="preview-box">
            <text class="preview-title">预览 · {{ feedName || '未命名' }}</text>
            <text v-for="(it, i) in previewItems" :key="i" class="preview-item">· {{ it.title }}</text>
          </view>
        </view>

        <view v-if="loadingJournals" class="loading"><text>加载中...</text></view>
        <view v-else-if="journals.length === 0" class="empty"><text>尚未关注任何期刊</text></view>
        <view v-else class="list">
          <view v-for="j in journals" :key="j.id" class="list-item-block">
            <view class="list-item">
              <view class="item-main" @click="goJournal(j.id)">
                <text class="item-name">{{ j.name }}</text>
                <text class="item-meta">
                  {{ j.source_type }}
                  <text v-if="j.content_type === 'preprint'"> · 预印本</text>
                  <text v-if="j.directory_status && j.directory_status !== 'public'"> · {{ dirStatusLabel(j.directory_status) }}</text>
                  · {{ freqLabel(j.push_frequency) }}
                </text>
              </view>
              <text class="btn-prefs" @click="cycleFreq(j)">频率</text>
              <text class="btn-unsub" @click="unsubscribe(j.id)">取消</text>
            </view>
            <view class="channel-row">
              <text
                :class="['chip', j.email_enabled !== false && 'on']"
                @click="toggleChannel(j, 'email_enabled')"
              >邮件</text>
              <text
                :class="['chip', j.wechat_enabled !== false && 'on']"
                @click="toggleChannel(j, 'wechat_enabled')"
              >微信</text>
            </view>
          </view>
        </view>
      </view>

      <view v-if="tab === 'authors'">
        <view class="add-bar">
          <input v-model="newAuthor" placeholder="作者姓名" class="add-input" />
          <button @click="addAuthor" :disabled="!newAuthor.trim()" class="btn-add">添加</button>
        </view>
        <view v-if="authors.length === 0" class="empty"><text>尚未追踪任何作者</text></view>
        <view v-else class="tag-list">
          <view v-for="a in authors" :key="a.id" class="tag-item">
            <text>{{ a.author_name }}</text>
            <text class="tag-close" @click="removeAuthor(a.id)">×</text>
          </view>
        </view>
      </view>

      <view v-if="tab === 'keywords'">
        <view class="add-bar">
          <input v-model="newKeyword" placeholder="关键词" class="add-input" />
          <button @click="addKeyword" :disabled="!newKeyword.trim()" class="btn-add">添加</button>
        </view>
        <view v-if="keywords.length === 0" class="empty"><text>尚未订阅任何关键词</text></view>
        <view v-else class="tag-list">
          <view v-for="k in keywords" :key="k.id" class="tag-item">
            <text>{{ k.keyword }}</text>
            <text class="tag-close" @click="removeKeyword(k.id)">×</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  getSubscribedJournals, unsubscribeJournal, updateJournalSubscriptionPrefs,
  getAuthors, addAuthor as addAuthorApi, removeAuthor as removeAuthorApi,
  getKeywords, addKeyword as addKeywordApi, removeKeyword as removeKeywordApi,
  type SubscribedJournal, type AuthorTracking, type KeywordSubscription,
} from '@/api/subscriptions'
import { addMyJournal, previewJournal, type PreviewItem } from '@/api/journals'

const auth = useAuthStore()
const tab = ref('journals')

const journals = ref<SubscribedJournal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])
const newAuthor = ref('')
const newKeyword = ref('')

const feedUrl = ref('')
const feedName = ref('')
const feedVisibility = ref<'private' | 'apply_public'>('private')
const previewItems = ref<PreviewItem[]>([])
const addingFeed = ref(false)

const FREQ_CYCLE = ['default', 'realtime', 'daily'] as const

function freqLabel(f?: string): string {
  if (f === 'realtime') return '实时'
  if (f === 'daily') return '每日'
  return '跟随全局'
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

function goJournal(id: string) {
  uni.navigateTo({ url: `/pages/journals/detail?id=${id}` })
}

onMounted(() => {
  if (!auth.isLoggedIn) return
  loadData()
})

async function loadData() {
  try {
    const [jr, ar, kr] = await Promise.all([
      getSubscribedJournals(),
      getAuthors(),
      getKeywords(),
    ])
    journals.value = jr.journals
    authors.value = ar.authors
    keywords.value = kr.keywords
  } finally {
    loadingJournals.value = false
  }
}

function goLogin() { uni.navigateTo({ url: '/pages/login/index' }) }

async function cycleFreq(j: SubscribedJournal) {
  const cur = j.push_frequency || 'default'
  const idx = Math.max(0, FREQ_CYCLE.indexOf(cur as any))
  const next = FREQ_CYCLE[(idx + 1) % FREQ_CYCLE.length]
  try {
    const updated = await updateJournalSubscriptionPrefs(j.id, { push_frequency: next })
    j.push_frequency = updated.push_frequency
    uni.showToast({ title: `频率 → ${freqLabel(next)}`, icon: 'none' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '更新失败', icon: 'none' })
  }
}

async function toggleChannel(j: SubscribedJournal, field: 'email_enabled' | 'wechat_enabled') {
  const cur = j[field] !== false
  const next = !cur
  try {
    const updated = await updateJournalSubscriptionPrefs(j.id, { [field]: next })
    j.email_enabled = updated.email_enabled
    j.wechat_enabled = updated.wechat_enabled
    uni.showToast({
      title: `${field === 'email_enabled' ? '邮件' : '微信'} → ${next ? '开' : '关'}`,
      icon: 'none',
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '更新失败', icon: 'none' })
  }
}

async function unsubscribe(id: string) {
  try {
    await unsubscribeJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
    uni.showToast({ title: '已取消关注', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

async function addFeed() {
  const url = feedUrl.value.trim()
  if (!url) {
    uni.showToast({ title: '请填写 RSS URL', icon: 'none' })
    return
  }
  addingFeed.value = true
  try {
    if (!feedName.value.trim() || !previewItems.value.length) {
      const preview = await previewJournal(url)
      if (!feedName.value.trim()) feedName.value = preview.name || ''
      previewItems.value = preview.items || []
    }
    const name = feedName.value.trim() || 'My Feed'
    const visibility = feedVisibility.value
    await addMyJournal(name, url, visibility)
    feedUrl.value = ''
    feedName.value = ''
    feedVisibility.value = 'private'
    previewItems.value = []
    journals.value = (await getSubscribedJournals()).journals
    uni.showToast({
      title: visibility === 'apply_public' ? '已添加并申请公开' : '已添加私有源',
      icon: 'success',
    })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  } finally {
    addingFeed.value = false
  }
}

async function addAuthor() {
  try {
    await addAuthorApi(newAuthor.value.trim())
    newAuthor.value = ''
    authors.value = (await getAuthors()).authors
    uni.showToast({ title: '已添加', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  }
}

async function removeAuthor(id: string) {
  try {
    await removeAuthorApi(id)
    authors.value = authors.value.filter(a => a.id !== id)
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

async function addKeyword() {
  try {
    await addKeywordApi(newKeyword.value.trim())
    newKeyword.value = ''
    keywords.value = (await getKeywords()).keywords
    uni.showToast({ title: '已添加', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '添加失败', icon: 'none' })
  }
}

async function removeKeyword(id: string) {
  try {
    await removeKeywordApi(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
</script>

<style scoped>
.container { min-height: 100vh; }
.tabs { display: flex; padding: 20rpx 30rpx; gap: 30rpx; background: #fff; border-bottom: 1rpx solid #eee; }
.tab { font-size: 30rpx; color: #666; padding-bottom: 8rpx; }
.tab.active { color: #3cc51f; font-weight: 500; border-bottom: 4rpx solid #3cc51f; }
.login-prompt { text-align: center; padding: 200rpx 40rpx; color: #999; font-size: 28rpx; }
.btn-login { margin-top: 30rpx; background: #3cc51f; color: #fff; border: none; border-radius: 12rpx; padding: 20rpx 60rpx; }
.loading, .empty { text-align: center; padding: 80rpx; color: #999; font-size: 28rpx; }
.list-item-block { background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.list-item { display: flex; align-items: center; padding: 24rpx 30rpx 8rpx; gap: 16rpx; }
.item-main { flex: 1; min-width: 0; }
.item-name { font-size: 28rpx; display: block; }
.item-meta { font-size: 22rpx; color: #999; margin-top: 4rpx; display: block; }
.btn-prefs { color: #3a7bd5; font-size: 26rpx; }
.btn-unsub { color: #e74c3c; font-size: 26rpx; }
.channel-row { display: flex; gap: 16rpx; padding: 0 30rpx 20rpx; }
.chip {
  font-size: 22rpx; padding: 6rpx 16rpx; border-radius: 8rpx;
  background: #f5f5f5; color: #999;
}
.chip.on { background: #e8f8e0; color: #3cc51f; }
.add-bar { display: flex; gap: 16rpx; padding: 20rpx 30rpx; background: #fff; }
.add-input { flex: 1; border: 1rpx solid #ddd; border-radius: 8rpx; padding: 16rpx 20rpx; font-size: 28rpx; margin-bottom: 12rpx; width: 100%; box-sizing: border-box; }
.btn-add { background: #3cc51f; color: #fff; border: none; border-radius: 8rpx; padding: 16rpx 30rpx; font-size: 28rpx; }
.add-feed { padding: 20rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.add-feed-row { display: flex; align-items: center; gap: 24rpx; margin-top: 8rpx; }
.vis-opt { display: flex; align-items: center; gap: 8rpx; font-size: 26rpx; color: #666; }
.radio { width: 24rpx; height: 24rpx; border-radius: 50%; border: 2rpx solid #ccc; display: inline-block; }
.radio.on { border-color: #3cc51f; background: #3cc51f; }
.preview-box { margin-top: 16rpx; padding: 16rpx; background: #f7f7f7; border-radius: 8rpx; }
.preview-title { font-size: 24rpx; color: #666; display: block; margin-bottom: 8rpx; }
.preview-item { font-size: 22rpx; color: #999; display: block; line-height: 1.5; }
.tag-list { display: flex; flex-wrap: wrap; padding: 20rpx 30rpx; gap: 16rpx; }
.tag-item { background: #e8f8e0; color: #3cc51f; padding: 12rpx 20rpx; border-radius: 8rpx; font-size: 26rpx; display: flex; align-items: center; gap: 12rpx; }
.tag-close { color: #999; font-size: 32rpx; }
</style>
