<template>
  <view class="container">
    <!-- Check login -->
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

      <!-- Journals tab -->
      <view v-if="tab === 'journals'">
        <view v-if="loadingJournals" class="loading"><text>加载中...</text></view>
        <view v-else-if="journals.length === 0" class="empty"><text>尚未关注任何期刊</text></view>
        <view v-else class="list">
          <view v-for="j in journals" :key="j.id" class="list-item">
            <text class="item-name">{{ j.name }}</text>
            <text class="item-type">{{ j.source_type }}</text>
            <text class="btn-unsub" @click="unsubscribe(j.id)">取消关注</text>
          </view>
        </view>
      </view>

      <!-- Authors tab -->
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

      <!-- Keywords tab -->
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
  getSubscribedJournals, unsubscribeJournal,
  getAuthors, addAuthor as addAuthorApi, removeAuthor as removeAuthorApi,
  getKeywords, addKeyword as addKeywordApi, removeKeyword as removeKeywordApi,
} from '@/api/subscriptions'
import type { Journal } from '@/api/journals'
import type { AuthorTracking, KeywordSubscription } from '@/api/subscriptions'

const auth = useAuthStore()
const tab = ref('journals')

const journals = ref<Journal[]>([])
const loadingJournals = ref(true)
const authors = ref<AuthorTracking[]>([])
const keywords = ref<KeywordSubscription[]>([])
const newAuthor = ref('')
const newKeyword = ref('')

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

async function unsubscribe(id: string) {
  try {
    await unsubscribeJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
    uni.showToast({ title: '已取消关注', icon: 'success' })
  } catch (e: any) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
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
.list-item { display: flex; align-items: center; padding: 24rpx 30rpx; background: #fff; border-bottom: 1rpx solid #f0f0f0; }
.item-name { flex: 1; font-size: 28rpx; }
.item-type { font-size: 22rpx; color: #999; margin-right: 20rpx; }
.btn-unsub { color: #e74c3c; font-size: 26rpx; }
.add-bar { display: flex; gap: 16rpx; padding: 20rpx 30rpx; background: #fff; }
.add-input { flex: 1; border: 1rpx solid #ddd; border-radius: 8rpx; padding: 16rpx 20rpx; font-size: 28rpx; }
.btn-add { background: #3cc51f; color: #fff; border: none; border-radius: 8rpx; padding: 16rpx 30rpx; font-size: 28rpx; }
.tag-list { display: flex; flex-wrap: wrap; padding: 20rpx 30rpx; gap: 16rpx; }
.tag-item { background: #e8f8e0; color: #3cc51f; padding: 12rpx 20rpx; border-radius: 8rpx; font-size: 26rpx; display: flex; align-items: center; gap: 12rpx; }
.tag-close { color: #999; font-size: 32rpx; }
</style>
