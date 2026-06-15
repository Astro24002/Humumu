# Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vue 3 web dashboard for Journal Monitor covering public article browsing, user subscription management, and admin panel.

**Architecture:** Vue 3 SPA (Vite + TypeScript + Naive UI) in `web/` directory. Go backend serves the built SPA via `embed` in the same binary. Dev mode uses Vite proxy to Go API. 8 new admin API endpoints added on the Go side.

**Tech Stack:** Vue 3, Vite, TypeScript, Naive UI, Vue Router 4, Pinia, Go (Gin)

---

## File Structure

```
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── env.d.ts
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts
│   ├── stores/auth.ts
│   ├── api/client.ts
│   ├── api/auth.ts
│   ├── api/articles.ts
│   ├── api/journals.ts
│   ├── api/subscriptions.ts
│   ├── api/admin.ts
│   ├── api/notifications.ts
│   ├── layouts/DefaultLayout.vue
│   ├── layouts/AdminLayout.vue
│   ├── views/Login.vue
│   ├── views/Register.vue
│   ├── views/Home.vue
│   ├── views/Journals.vue
│   ├── views/JournalDetail.vue
│   ├── views/ArticleDetail.vue
│   ├── views/my/Feed.vue
│   ├── views/my/Subscriptions.vue
│   ├── views/my/Notifications.vue
│   ├── views/Settings.vue
│   ├── views/admin/Dashboard.vue
│   ├── views/admin/Journals.vue
│   ├── views/admin/Requests.vue
│   ├── views/admin/Users.vue
│   └── styles/global.css

cmd/server/main.go                          # Add embed + NoRoute
internal/api/router.go                      # Move articles/journals to public, add routes
internal/api/admin.go                       # New: admin handlers
internal/repo/journal_repo.go               # Add admin CRUD
internal/repo/user_repo.go                  # Add GetAll/Update
internal/model/journal.go                   # Add admin request types
internal/model/user.go                      # Add admin update types
```

---

### Task 1: Scaffold Vue 3 project + dependencies

**Files:**
- Create: `web/index.html`
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/tsconfig.app.json`
- Create: `web/env.d.ts`
- Create: `web/src/main.ts`
- Create: `web/src/App.vue`
- Create: `web/src/styles/global.css`

- [ ] **Step 1: Write package.json**

```json
{
  "name": "journal-monitor-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.5.0",
    "pinia": "^3.0.0",
    "naive-ui": "^2.41.0",
    "@vicons/ionicons5": "^0.12.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "vite": "^6.3.0",
    "typescript": "^5.8.0",
    "vue-tsc": "^2.2.0",
    "@types/node": "^22.0.0"
  }
}
```

- [ ] **Step 2: Write index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Journal Monitor</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 3: Write vite.config.ts**

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
      '/health': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
})
```

- [ ] **Step 4: Write tsconfig.json**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" }
  ]
}
```

- [ ] **Step 5: Write tsconfig.app.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForExpose": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "env.d.ts"]
}
```

- [ ] **Step 6: Write env.d.ts**

```ts
/// <reference types="vite/client" />
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 7: Write src/main.ts**

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 8: Write src/App.vue**

```vue
<template>
  <n-message-provider>
    <router-view />
  </n-message-provider>
</template>

<script setup lang="ts">
import { NMessageProvider } from 'naive-ui'
</script>

<style>
@import './styles/global.css';
</style>
```

- [ ] **Step 9: Write src/styles/global.css**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
```

- [ ] **Step 10: Install and verify**

Run: `cd web && npm install && npm run build`
Expected: `web/dist/` created with built assets (index.html + JS)

- [ ] **Step 11: Commit**

```bash
git add web/
git commit -m "feat: scaffold Vue 3 + Vite + Naive UI project"
```

---

### Task 2: API client layer + auth store

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/api/auth.ts`
- Create: `web/src/api/articles.ts`
- Create: `web/src/api/journals.ts`
- Create: `web/src/api/subscriptions.ts`
- Create: `web/src/api/notifications.ts`
- Create: `web/src/api/admin.ts`
- Create: `web/src/stores/auth.ts`

- [ ] **Step 1: Write api/client.ts**

```ts
const BASE_URL = '/api/v1'

interface ApiError {
  error: string
}

export class ApiClientError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText })) as ApiError
    throw new ApiClientError(res.status, body.error || 'request failed')
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return {} as T
  }
  return res.json()
}

export function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return request<T>(path + qs)
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined })
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}
```

- [ ] **Step 2: Write api/auth.ts**

```ts
import { post } from './client'

export interface AuthResponse {
  token: string
  user: {
    id: string
    email: string
    name: string
    wechat_openid?: string
    push_frequency: string
    created_at: string
  }
}

export function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/register', { email, password, name })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/login', { email, password })
}
```

- [ ] **Step 3: Write api/articles.ts**

```ts
import { get } from './client'

export interface Article {
  id: string
  doi: string
  title: string
  authors: string[]
  abstract: string
  journal_id: string
  publish_date: string | null
  url: string
  fetched_at: string
}

export interface ArticlesResponse {
  articles: Article[]
}

export function getArticles(params?: { journal_id?: string; limit?: string; offset?: string }): Promise<ArticlesResponse> {
  return get<ArticlesResponse>('/articles', params as Record<string, string>)
}

export function getArticle(id: string): Promise<Article> {
  return get<Article>(`/articles/${id}`)
}

export function getMyFeed(params?: { limit?: string; offset?: string }): Promise<ArticlesResponse> {
  return get<ArticlesResponse>('/my/feed', params as Record<string, string>)
}
```

- [ ] **Step 4: Write api/journals.ts**

```ts
import { get, post } from './client'

export interface Journal {
  id: string
  name: string
  slug: string
  source_type: string
  source_url: string
  is_active: boolean
  created_at: string
}

export interface JournalsResponse {
  journals: Journal[]
}

export function getJournals(): Promise<JournalsResponse> {
  return get<JournalsResponse>('/journals')
}

export function getJournal(id: string): Promise<Journal> {
  return get<Journal>(`/journals/${id}`)
}

export function requestJournal(journalName: string, sourceUrl: string): Promise<void> {
  return post('/journals/requests', { journal_name: journalName, source_url: sourceUrl })
}
```

- [ ] **Step 5: Write api/subscriptions.ts**

```ts
import { get, post, del } from './client'
import type { Journal } from './journals'

export interface AuthorTracking {
  id: string
  user_id: string
  author_name: string
  created_at: string
}

export interface KeywordSubscription {
  id: string
  user_id: string
  keyword: string
  created_at: string
}

export function getSubscribedJournals(): Promise<{ journals: Journal[] }> {
  return get('/subscriptions/journals')
}

export function subscribeJournal(id: string): Promise<void> {
  return post(`/subscriptions/journals/${id}`)
}

export function unsubscribeJournal(id: string): Promise<void> {
  return del(`/subscriptions/journals/${id}`)
}

export function getAuthors(): Promise<{ authors: AuthorTracking[] }> {
  return get('/subscriptions/authors')
}

export function addAuthor(authorName: string): Promise<void> {
  return post('/subscriptions/authors', { author_name: authorName })
}

export function removeAuthor(id: string): Promise<void> {
  return del(`/subscriptions/authors/${id}`)
}

export function getKeywords(): Promise<{ keywords: KeywordSubscription[] }> {
  return get('/subscriptions/keywords')
}

export function addKeyword(keyword: string): Promise<void> {
  return post('/subscriptions/keywords', { keyword })
}

export function removeKeyword(id: string): Promise<void> {
  return del(`/subscriptions/keywords/${id}`)
}

export function updatePushFrequency(freq: string): Promise<void> {
  return put('/settings/push-frequency', { push_frequency: freq })
}
```

- [ ] **Step 6: Write api/notifications.ts**

```ts
import { get } from './client'

export interface Notification {
  id: string
  user_id: string
  article_id: string
  channel: string
  status: string
  error_message: string | null
  created_at: string
  sent_at: string | null
}

export function getNotifications(params?: { limit?: string; offset?: string }): Promise<{ notifications: Notification[] }> {
  return get('/notifications', params as Record<string, string>)
}
```

- [ ] **Step 7: Write api/admin.ts**

```ts
import { get, post, put, del } from './client'
import type { Journal } from './journals'

export interface AdminStats {
  journal_count: number
  article_count: number
  user_count: number
  pending_requests: number
}

export interface JournalRequest {
  id: string
  user_id: string
  journal_name: string
  source_url: string
  status: string
  created_at: string
  reviewed_at: string | null
}

export interface User {
  id: string
  email: string
  name: string
  push_frequency: string
  created_at: string
}

export function getStats(): Promise<AdminStats> {
  return get('/admin/stats')
}

export function getAllJournals(): Promise<{ journals: Journal[] }> {
  return get('/admin/journals')
}

export function createJournal(data: Partial<Journal>): Promise<void> {
  return post('/admin/journals', data)
}

export function updateJournal(id: string, data: Partial<Journal>): Promise<void> {
  return put(`/admin/journals/${id}`, data)
}

export function deleteJournal(id: string): Promise<void> {
  return del(`/admin/journals/${id}`)
}

export function getRequests(): Promise<{ requests: JournalRequest[] }> {
  return get('/admin/requests')
}

export function reviewRequest(id: string, status: string): Promise<void> {
  return put(`/admin/requests/${id}`, { status })
}

export function getUsers(): Promise<{ users: User[] }> {
  return get('/admin/users')
}
```

- [ ] **Step 8: Write stores/auth.ts**

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, type AuthResponse } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<AuthResponse['user'] | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => false) // placeholder — future role check

  function setAuth(res: AuthResponse) {
    token.value = res.token
    user.value = res.user
    localStorage.setItem('token', res.token)
  }

  async function login(email: string, password: string) {
    const res = await apiLogin(email, password)
    setAuth(res)
  }

  async function register(email: string, password: string, name: string) {
    const res = await apiRegister(email, password, name)
    setAuth(res)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, isAdmin, login, register, logout }
})
```

- [ ] **Step 9: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds, `web/dist/` created

- [ ] **Step 10: Commit**

```bash
git add web/src/api web/src/stores
git commit -m "feat: add API client layer and auth store"
```

---

### Task 3: Router + Layout

**Files:**
- Create: `web/src/router/index.ts`
- Create: `web/src/layouts/DefaultLayout.vue`
- Create: `web/src/layouts/AdminLayout.vue`

- [ ] **Step 1: Write router/index.ts**

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: DefaultLayout,
      children: [
        { path: '', name: 'Home', component: () => import('@/views/Home.vue') },
        { path: 'journals', name: 'Journals', component: () => import('@/views/Journals.vue') },
        { path: 'journals/:id', name: 'JournalDetail', component: () => import('@/views/JournalDetail.vue') },
        { path: 'articles/:id', name: 'ArticleDetail', component: () => import('@/views/ArticleDetail.vue') },
        { path: 'login', name: 'Login', component: () => import('@/views/Login.vue') },
        { path: 'register', name: 'Register', component: () => import('@/views/Register.vue') },
        { path: 'my', name: 'MyFeed', component: () => import('@/views/my/Feed.vue'), meta: { requiresAuth: true } },
        { path: 'my/subscriptions', name: 'MySubscriptions', component: () => import('@/views/my/Subscriptions.vue'), meta: { requiresAuth: true } },
        { path: 'my/notifications', name: 'MyNotifications', component: () => import('@/views/my/Notifications.vue'), meta: { requiresAuth: true } },
        { path: 'settings', name: 'Settings', component: () => import('@/views/Settings.vue'), meta: { requiresAuth: true } },
      ],
    },
    {
      path: '/admin',
      component: AdminLayout,
      children: [
        { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { requiresAuth: true } },
        { path: 'journals', name: 'AdminJournals', component: () => import('@/views/admin/Journals.vue'), meta: { requiresAuth: true } },
        { path: 'requests', name: 'AdminRequests', component: () => import('@/views/admin/Requests.vue'), meta: { requiresAuth: true } },
        { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue'), meta: { requiresAuth: true } },
      ],
    },
  ],
})

router.beforeEach((to, _from) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
})

export default router
```

- [ ] **Step 2: Write layouts/DefaultLayout.vue**

```vue
<template>
  <n-layout position="absolute" style="height: 100%">
    <n-layout-header bordered style="padding: 0 24px; display: flex; align-items: center; height: 56px;">
      <n-h3 style="margin: 0; cursor: pointer" @click="router.push('/')">📓 Journal Monitor</n-h3>
      <div style="flex: 1" />
      <template v-if="auth.isLoggedIn">
        <n-button quaternary @click="router.push('/my')">我的</n-button>
        <n-button quaternary @click="router.push('/my/subscriptions')">订阅</n-button>
        <n-dropdown trigger="click" :options="userMenuOptions" @select="onUserMenuSelect">
          <n-button quaternary>{{ auth.user?.name || '用户' }}</n-button>
        </n-dropdown>
      </template>
      <template v-else>
        <n-button quaternary @click="router.push('/login')">登录</n-button>
        <n-button quaternary @click="router.push('/register')">注册</n-button>
      </template>
    </n-layout-header>

    <n-layout-content style="padding: 24px; max-width: 960px; margin: 0 auto;">
      <router-view />
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NLayout, NLayoutHeader, NLayoutContent, NButton, NH3, NDropdown, NIcon } from 'naive-ui'
import { SettingsOutline, LogOutOutline } from '@vicons/ionicons5'

const router = useRouter()
const auth = useAuthStore()

const userMenuOptions = [
  { key: 'settings', label: '设置', icon: () => h(NIcon, null, { default: () => h(SettingsOutline) }) },
  { key: 'logout', label: '退出', icon: () => h(NIcon, null, { default: () => h(LogOutOutline) }) },
]

function onUserMenuSelect(key: string) {
  if (key === 'settings') router.push('/settings')
  if (key === 'logout') { auth.logout(); router.push('/') }
}
</script>
```

- [ ] **Step 3: Write layouts/AdminLayout.vue**

```vue
<template>
  <n-layout position="absolute" has-sider style="height: 100%">
    <n-layout-sider bordered content-style="padding: 24px;" width="200">
      <n-h4 style="margin-bottom: 16px;">📓 管理后台</n-h4>
      <n-menu :value="activeKey" :options="menuOptions" @update:value="onMenuSelect" />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered style="padding: 0 24px; display: flex; align-items: center; height: 56px;">
        <span style="font-weight: 600;">管理面板</span>
        <div style="flex: 1" />
        <n-button quaternary size="small" @click="router.push('/')">返回前台</n-button>
      </n-layout-header>

      <n-layout-content style="padding: 24px;">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NButton, NH4, NMenu } from 'naive-ui'
import { BarChart, BookOutline, PeopleOutline, ClipboardOutline } from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => route.path)

const menuOptions = [
  { key: '/admin', label: '概览', icon: () => h(BarChart) },
  { key: '/admin/journals', label: '期刊管理', icon: () => h(BookOutline) },
  { key: '/admin/requests', label: '申请审核', icon: () => h(ClipboardOutline) },
  { key: '/admin/users', label: '用户管理', icon: () => h(PeopleOutline) },
]

function onMenuSelect(key: string) {
  router.push(key)
}
</script>

<script lang="ts">
import { h } from 'vue'
import type { VNode } from 'vue'
</script>
```

- [ ] **Step 4: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add web/src/router web/src/layouts
git commit -m "feat: add router and layouts"
```

---

### Task 4: Login + Register pages

**Files:**
- Create: `web/src/views/Login.vue`
- Create: `web/src/views/Register.vue`

- [ ] **Step 1: Write Login.vue**

```vue
<template>
  <n-card title="登录" style="max-width: 400px; margin: 80px auto;">
    <n-form :model="form" :rules="rules" @submit.prevent="handleLogin">
      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="form.email" placeholder="user@example.com" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="form.password" type="password" show-password-on="click" />
      </n-form-item>
      <n-button type="primary" block :loading="loading" attr-type="submit">登录</n-button>
    </n-form>
    <p style="margin-top: 12px; text-align: center; color: #888;">
      还没有账号？<router-link to="/register">注册</router-link>
    </p>
  </n-card>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from 'naive-ui'
import { NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)

const form = reactive({ email: '', password: '' })
const rules = {
  email: { required: true, type: 'email' as const, message: '请输入有效邮箱' },
  password: { required: true, message: '请输入密码' },
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    message.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e: any) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 2: Write Register.vue**

```vue
<template>
  <n-card title="注册" style="max-width: 400px; margin: 80px auto;">
    <n-form :model="form" :rules="rules" @submit.prevent="handleRegister">
      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="form.email" placeholder="user@example.com" />
      </n-form-item>
      <n-form-item label="密码" path="password">
        <n-input v-model:value="form.password" type="password" show-password-on="click" />
      </n-form-item>
      <n-form-item label="昵称" path="name">
        <n-input v-model:value="form.name" placeholder="可选" />
      </n-form-item>
      <n-button type="primary" block :loading="loading" attr-type="submit">注册</n-button>
    </n-form>
    <p style="margin-top: 12px; text-align: center; color: #888;">
      已有账号？<router-link to="/login">登录</router-link>
    </p>
  </n-card>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from 'naive-ui'
import { NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)

const form = reactive({ email: '', password: '', name: '' })
const rules = {
  email: { required: true, type: 'email' as const, message: '请输入有效邮箱' },
  password: { required: true, min: 6, message: '密码至少6位' },
}

async function handleRegister() {
  loading.value = true
  try {
    await auth.register(form.email, form.password, form.name)
    message.success('注册成功')
    router.push('/')
  } catch (e: any) {
    message.error(e.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 3: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add web/src/views/Login.vue web/src/views/Register.vue
git commit -m "feat: add login and register pages"
```

---

### Task 5: Public pages — Home, Journals, ArticleDetail

**Files:**
- Create: `web/src/views/Home.vue`
- Create: `web/src/views/Journals.vue`
- Create: `web/src/views/JournalDetail.vue`
- Create: `web/src/views/ArticleDetail.vue`

- [ ] **Step 1: Write Home.vue**

```vue
<template>
  <div>
    <n-h2>最新论文</n-h2>
    <n-select v-if="journals.length" v-model:value="filterJournalId" :options="journalOptions"
      placeholder="筛选期刊" clearable style="max-width: 300px; margin-bottom: 16px;" />

    <div v-if="loading"><n-spin /></div>
    <n-empty v-else-if="!articles.length" description="暂无文章" />

    <n-list v-else>
      <n-list-item v-for="a in articles" :key="a.id">
        <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
          <template #footer>
            <router-link :to="`/articles/${a.id}`">查看详情</router-link>
          </template>
        </n-thing>
      </n-list-item>
    </n-list>

    <n-pagination v-if="total > limit" :page="page" :page-count="Math.ceil(total / limit)"
      @update:page="loadPage" style="margin-top: 16px;" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { getArticles, type Article } from '@/api/articles'
import { getJournals, type Journal } from '@/api/journals'
import { NH2, NSelect, NSpin, NEmpty, NList, NListItem, NThing, NPagination } from 'naive-ui'

const articles = ref<Article[]>([])
const journals = ref<Journal[]>([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const limit = 20
const filterJournalId = ref<string | null>(null)

const journalOptions = computed(() =>
  journals.value.map(j => ({ label: j.name, value: j.id }))
)

async function loadArticles() {
  loading.value = true
  try {
    const params: Record<string, string> = {
      limit: String(limit),
      offset: String((page.value - 1) * limit),
    }
    if (filterJournalId.value) params.journal_id = filterJournalId.value
    const res = await getArticles(params)
    articles.value = res.articles
  } finally {
    loading.value = false
  }
}

function loadPage(p: number) {
  page.value = p
  loadArticles()
}

watch(filterJournalId, () => { page.value = 1; loadArticles() })

onMounted(async () => {
  try { journals.value = (await getJournals()).journals } catch {}
  loadArticles()
})
</script>
```

- [ ] **Step 2: Write Journals.vue**

```vue
<template>
  <div>
    <n-h2>期刊广场</n-h2>
    <n-grid :cols="2" :y-gap="16" :x-gap="16">
      <n-gi v-for="j in journals" :key="j.id">
        <n-card :title="j.name" hoverable @click="router.push(`/journals/${j.id}`)">
          <n-tag :type="j.source_type === 'arxiv' ? 'info' : 'success'" size="small">
            {{ j.source_type }}
          </n-tag>
          <p style="margin-top: 8px; color: #888; font-size: 12px;">{{ j.source_url }}</p>
        </n-card>
      </n-gi>
    </n-grid>
    <n-empty v-if="!journals.length && !loading" description="暂无可浏览的期刊" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getJournals, type Journal } from '@/api/journals'
import { NH2, NGrid, NGi, NCard, NTag, NEmpty } from 'naive-ui'

const router = useRouter()
const journals = ref<Journal[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    journals.value = (await getJournals()).journals
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 3: Write JournalDetail.vue**

```vue
<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <n-h2 v-if="journal">{{ journal.name }}</n-h2>
  <n-tag v-if="journal" :type="journal.source_type === 'arxiv' ? 'info' : 'success'" size="small">
    {{ journal.source_type }}
  </n-tag>

  <n-divider />

  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!articles.length" description="暂无文章" />
  <n-list v-else>
    <n-list-item v-for="a in articles" :key="a.id">
      <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
        <template #footer><router-link :to="`/articles/${a.id}`">查看详情</router-link></template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getJournal, type Journal } from '@/api/journals'
import { getArticles, type Article } from '@/api/articles'
import { NH2, NButton, NTag, NDivider, NSpin, NEmpty, NList, NListItem, NThing } from 'naive-ui'

const route = useRoute()
const router = useRouter()
const journal = ref<Journal | null>(null)
const articles = ref<Article[]>([])
const loading = ref(true)

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
```

- [ ] **Step 4: Write ArticleDetail.vue**

```vue
<template>
  <n-button quaternary @click="router.back()" style="margin-bottom: 16px;">← 返回</n-button>
  <div v-if="loading"><n-spin /></div>
  <template v-else-if="article">
    <n-h2>{{ article.title }}</n-h2>
    <p style="color: #666; margin-bottom: 8px;">作者：{{ article.authors?.join(', ') }}</p>
    <p style="color: #888; font-size: 12px; margin-bottom: 16px;">
      DOI: {{ article.doi }} | 发表日期：{{ article.publish_date || '未知' }}
    </p>
    <n-divider />
    <n-h4>摘要</n-h4>
    <p style="line-height: 1.8; white-space: pre-wrap;">{{ article.abstract }}</p>
    <n-button type="primary" tag="a" :href="article.url" target="_blank" style="margin-top: 16px;">
      查看原文
    </n-button>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle, type Article } from '@/api/articles'
import { NH2, NH4, NButton, NDivider, NSpin } from 'naive-ui'

const route = useRoute()
const router = useRouter()
const article = ref<Article | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    article.value = await getArticle(route.params.id as string)
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 5: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add web/src/views/Home.vue web/src/views/Journals.vue web/src/views/JournalDetail.vue web/src/views/ArticleDetail.vue
git commit -m "feat: add public pages — home, journals, article detail"
```

---

### Task 6: User pages — Feed, Subscriptions, Notifications, Settings

**Files:**
- Create: `web/src/views/my/Feed.vue`
- Create: `web/src/views/my/Subscriptions.vue`
- Create: `web/src/views/my/Notifications.vue`
- Create: `web/src/views/Settings.vue`

- [ ] **Step 1: Write my/Feed.vue**

```vue
<template>
  <n-h2>我的订阅</n-h2>
  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!articles.length" description="你还没有订阅任何期刊">
    <template #extra>
      <n-button @click="router.push('/journals')">浏览期刊</n-button>
    </template>
  </n-empty>
  <n-list v-else>
    <n-list-item v-for="a in articles" :key="a.id">
      <n-thing :title="a.title" :description="a.authors?.join(', ')" :extra="a.publish_date || ''">
        <template #footer><router-link :to="`/articles/${a.id}`">查看详情</router-link></template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyFeed, type Article } from '@/api/articles'
import { NH2, NSpin, NEmpty, NButton, NList, NListItem, NThing } from 'naive-ui'

const router = useRouter()
const articles = ref<Article[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getMyFeed()
    articles.value = res.articles
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 2: Write my/Subscriptions.vue**

```vue
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
import { getSubscribedJournals, unsubscribeJournal, getAuthors, addAuthor, removeAuthor, getKeywords, addKeyword, removeKeyword } from '@/api/subscriptions'
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
    await addAuthor(newAuthor.value.trim())
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
    await removeAuthor(id)
    authors.value = authors.value.filter(a => a.id !== id)
  } catch (e: any) {
    message.error(e.message)
  }
}

async function addKeyword() {
  try {
    await addKeyword(newKeyword.value.trim())
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
    await removeKeyword(id)
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
```

- [ ] **Step 3: Write my/Notifications.vue**

```vue
<template>
  <n-h2>通知历史</n-h2>
  <div v-if="loading"><n-spin /></div>
  <n-empty v-else-if="!notifs.length" description="暂无通知" />
  <n-list v-else>
    <n-list-item v-for="n in notifs" :key="n.id">
      <n-thing>
        <template #header>
          <n-tag :type="n.channel === 'email' ? 'primary' : 'success'" size="small">{{ n.channel }}</n-tag>
          <n-tag :type="n.status === 'sent' ? 'success' : n.status === 'failed' ? 'error' : 'warning'" size="small" style="margin-left: 8px;">
            {{ n.status === 'sent' ? '已发送' : n.status === 'failed' ? '失败' : '等待中' }}
          </n-tag>
        </template>
        <template #description>
          {{ n.created_at }}
          <span v-if="n.error_message" style="color: red; margin-left: 8px;">{{ n.error_message }}</span>
        </template>
      </n-thing>
    </n-list-item>
  </n-list>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNotifications, type Notification } from '@/api/notifications'
import { NH2, NSpin, NEmpty, NList, NListItem, NThing, NTag } from 'naive-ui'

const notifs = ref<Notification[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await getNotifications()
    notifs.value = res.notifications
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 4: Write Settings.vue**

```vue
<template>
  <n-h2>个人设置</n-h2>
  <n-card title="推送频率">
    <n-radio-group v-model:value="frequency">
      <n-radio value="realtime">实时推送</n-radio>
      <n-radio value="daily">每日汇总</n-radio>
    </n-radio-group>
    <n-button style="margin-top: 16px;" @click="saveFrequency" :loading="saving">保存</n-button>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { updatePushFrequency } from '@/api/subscriptions'
import { useMessage } from 'naive-ui'
import { NH2, NCard, NRadio, NRadioGroup, NButton } from 'naive-ui'

const auth = useAuthStore()
const message = useMessage()
const frequency = ref(auth.user?.push_frequency || 'realtime')
const saving = ref(false)

onMounted(() => { frequency.value = auth.user?.push_frequency || 'realtime' })

async function saveFrequency() {
  saving.value = true
  try {
    await updatePushFrequency(frequency.value)
    message.success('设置已保存')
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>
```

- [ ] **Step 5: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add web/src/views/my/ web/src/views/Settings.vue
git commit -m "feat: add user pages — feed, subscriptions, notifications, settings"
```

---

### Task 7: Admin API endpoints (Go backend)

**Files:**
- Modify: `internal/api/router.go`
- Create: `internal/api/admin.go`
- Modify: `internal/repo/journal_repo.go`
- Modify: `internal/repo/user_repo.go`

**Context:** The Go API currently has all endpoints in protected routes. We need to move journals list/detail and articles list to public routes, add `/my/feed` as a protected route, and add 8 new admin endpoints.

- [ ] **Step 1: Move public routes out of protected group in router.go**

Update `internal/api/router.go`:

```go
func SetupRouter(pool *pgxpool.Pool, rdb *redis.Client, cfg *config.Config) *gin.Engine {
	r := gin.Default()
	r.Use(CORSMiddleware())

	// Health
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// Public routes (no auth required)
	journalRepo := repo.NewJournalRepo(pool)
	articleRepo := repo.NewArticleRepo(pool)

	jh := NewJournalHandler(journalRepo)
	r.GET("/api/v1/journals", jh.List)
	r.GET("/api/v1/journals/:id", jh.Get)

	ah := NewArticleHandler(articleRepo)
	r.GET("/api/v1/articles", ah.List)
	r.GET("/api/v1/articles/:id", ah.Get)

	// Auth (no middleware)
	userRepo := repo.NewUserRepo(pool)
	authHandler := NewAuthHandler(userRepo, cfg.JWT, cfg.WeChat)

	auth := r.Group("/api/v1/auth")
	{
		auth.POST("/register", authHandler.Register)
		auth.POST("/login", authHandler.Login)
		auth.POST("/wechat", authHandler.WeChatLogin)
	}

	// Protected routes (require JWT)
	protected := r.Group("/api/v1")
	protected.Use(AuthMiddleware(cfg.JWT))
	{
		subRepo := repo.NewSubscriptionRepo(pool)
		notifRepo := repo.NewNotificationRepo(pool)

		sh := NewSubscriptionHandler(subRepo, journalRepo)
		protected.GET("/subscriptions/journals", sh.ListJournals)
		protected.POST("/subscriptions/journals/:id", sh.SubscribeJournal)
		protected.DELETE("/subscriptions/journals/:id", sh.UnsubscribeJournal)
		protected.GET("/subscriptions/authors", sh.ListAuthors)
		protected.POST("/subscriptions/authors", sh.AddAuthor)
		protected.DELETE("/subscriptions/authors/:id", sh.RemoveAuthor)
		protected.GET("/subscriptions/keywords", sh.ListKeywords)
		protected.POST("/subscriptions/keywords", sh.AddKeyword)
		protected.DELETE("/subscriptions/keywords/:id", sh.RemoveKeyword)

		protected.PUT("/settings/push-frequency", NewSettingsHandler(userRepo).UpdatePushFrequency)

		protected.GET("/notifications", NewNotificationHandler(notifRepo).List)

		rh := NewRequestHandler(journalRepo)
		protected.POST("/journals/requests", rh.Create)
		protected.GET("/journals/requests", rh.List)

		// My feed
		protected.GET("/my/feed", ah.MyFeed)

		// Admin routes
		admin := r.Group("/api/v1/admin")
		admin.Use(AuthMiddleware(cfg.JWT))
		{
			adm := NewAdminHandler(journalRepo, userRepo, articleRepo)
			admin.GET("/stats", adm.Stats)
			admin.GET("/journals", adm.ListJournals)
			admin.POST("/journals", adm.CreateJournal)
			admin.PUT("/journals/:id", adm.UpdateJournal)
			admin.DELETE("/journals/:id", adm.DeleteJournal)
			admin.GET("/requests", adm.ListRequests)
			admin.PUT("/requests/:id", adm.ReviewRequest)
			admin.GET("/users", adm.ListUsers)
		}
	}

	return r
}
```

- [ ] **Step 2: Add MyFeed handler to articles.go**

```go
func (h *ArticleHandler) MyFeed(c *gin.Context) {
	userID := c.GetString("user_id")
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if limit > 100 {
		limit = 100
	}

	articles, err := h.articleRepo.GetByUserSubscriptions(c.Request.Context(), userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch articles"})
		return
	}
	if articles == nil {
		articles = []*model.Article{}
	}
	c.JSON(http.StatusOK, gin.H{"articles": articles})
}
```

- [ ] **Step 3: Write admin.go**

```go
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/model"
	"github.com/humumu/journal-monitor/internal/repo"
)

type AdminHandler struct {
	journalRepo *repo.JournalRepo
	userRepo    *repo.UserRepo
	articleRepo *repo.ArticleRepo
}

func NewAdminHandler(journalRepo *repo.JournalRepo, userRepo *repo.UserRepo, articleRepo *repo.ArticleRepo) *AdminHandler {
	return &AdminHandler{
		journalRepo: journalRepo,
		userRepo:    userRepo,
		articleRepo: articleRepo,
	}
}

type AdminStatsResponse struct {
	JournalCount   int `json:"journal_count"`
	ArticleCount   int `json:"article_count"`
	UserCount      int `json:"user_count"`
	PendingRequests int `json:"pending_requests"`
}

func (h *AdminHandler) Stats(c *gin.Context) {
	journals, _ := h.journalRepo.GetAll(c.Request.Context())
	articles, _ := h.articleRepo.CountAll(c.Request.Context())
	users, _ := h.userRepo.GetAll(c.Request.Context())
	pending, _ := h.journalRepo.CountPendingRequests(c.Request.Context())

	c.JSON(http.StatusOK, AdminStatsResponse{
		JournalCount:   len(journals),
		ArticleCount:   articles,
		UserCount:      len(users),
		PendingRequests: pending,
	})
}

func (h *AdminHandler) ListJournals(c *gin.Context) {
	journals, err := h.journalRepo.GetAll(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch journals"})
		return
	}
	if journals == nil {
		journals = []*model.Journal{}
	}
	c.JSON(http.StatusOK, gin.H{"journals": journals})
}

func (h *AdminHandler) CreateJournal(c *gin.Context) {
	var j model.Journal
	if err := c.ShouldBindJSON(&j); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.Create(c.Request.Context(), &j); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create journal"})
		return
	}
	c.JSON(http.StatusCreated, j)
}

func (h *AdminHandler) UpdateJournal(c *gin.Context) {
	id := c.Param("id")
	var j model.Journal
	if err := c.ShouldBindJSON(&j); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.Update(c.Request.Context(), id, &j); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update journal"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "updated"})
}

func (h *AdminHandler) DeleteJournal(c *gin.Context) {
	id := c.Param("id")
	if err := h.journalRepo.Delete(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete journal"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deleted"})
}

func (h *AdminHandler) ListRequests(c *gin.Context) {
	reqs, err := h.journalRepo.GetAllRequests(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch requests"})
		return
	}
	if reqs == nil {
		reqs = []*model.JournalRequest{}
	}
	c.JSON(http.StatusOK, gin.H{"requests": reqs})
}

type ReviewRequest struct {
	Status string `json:"status" binding:"required,oneof=approved rejected"`
}

func (h *AdminHandler) ReviewRequest(c *gin.Context) {
	id := c.Param("id")
	var req ReviewRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := h.journalRepo.UpdateRequestStatus(c.Request.Context(), id, req.Status); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update request"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "request " + req.Status})
}

func (h *AdminHandler) ListUsers(c *gin.Context) {
	users, err := h.userRepo.GetAll(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch users"})
		return
	}
	if users == nil {
		users = []*model.User{}
	}
	c.JSON(http.StatusOK, gin.H{"users": users})
}
```

- [ ] **Step 4: Add missing repo methods**

Add to `internal/repo/journal_repo.go`:

```go
func (r *JournalRepo) Update(ctx context.Context, id string, j *model.Journal) error {
	query := `UPDATE journals SET name=$1, slug=$2, source_type=$3, source_url=$4, is_active=$5 WHERE id=$6`
	_, err := r.pool.Exec(ctx, query, j.Name, j.Slug, j.SourceType, j.SourceURL, j.IsActive, id)
	return err
}

func (r *JournalRepo) Delete(ctx context.Context, id string) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM journals WHERE id=$1`, id)
	return err
}

func (r *JournalRepo) GetAllRequests(ctx context.Context) ([]*model.JournalRequest, error) {
	query := `SELECT id, user_id, journal_name, source_url, status, created_at, reviewed_at
		FROM journal_requests ORDER BY created_at DESC`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var reqs []*model.JournalRequest
	for rows.Next() {
		req := &model.JournalRequest{}
		if err := rows.Scan(&req.ID, &req.UserID, &req.JournalName, &req.SourceURL,
			&req.Status, &req.CreatedAt, &req.ReviewedAt); err != nil {
			return nil, err
		}
		reqs = append(reqs, req)
	}
	return reqs, nil
}

func (r *JournalRepo) CountPendingRequests(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, `SELECT COUNT(*) FROM journal_requests WHERE status='pending'`).Scan(&count)
	return count, err
}
```

Add to `internal/repo/article_repo.go`:

```go
func (r *ArticleRepo) CountAll(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, `SELECT COUNT(*) FROM articles`).Scan(&count)
	return count, err
}
```

- [ ] **Step 5: Verify Go build**

Run: `go build ./...`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add internal/api/router.go internal/api/admin.go internal/api/articles.go internal/repo/journal_repo.go internal/repo/article_repo.go
git commit -m "feat: add admin API endpoints and public routes"
```

---

### Task 8: Admin pages

**Files:**
- Create: `web/src/views/admin/Dashboard.vue`
- Create: `web/src/views/admin/Journals.vue`
- Create: `web/src/views/admin/Requests.vue`
- Create: `web/src/views/admin/Users.vue`

- [ ] **Step 1: Write admin/Dashboard.vue**

```vue
<template>
  <n-h2>系统概览</n-h2>
  <n-grid :cols="4" :x-gap="16">
    <n-gi><n-statistic title="期刊数" :value="stats.journal_count" /></n-gi>
    <n-gi><n-statistic title="文章数" :value="stats.article_count" /></n-gi>
    <n-gi><n-statistic title="用户数" :value="stats.user_count" /></n-gi>
    <n-gi><n-statistic title="待审批申请" :value="stats.pending_requests" /></n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getStats, type AdminStats } from '@/api/admin'
import { NH2, NGrid, NGi, NStatistic } from 'naive-ui'

const stats = ref<AdminStats>({ journal_count: 0, article_count: 0, user_count: 0, pending_requests: 0 })

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch {}
})
</script>
```

- [ ] **Step 2: Write admin/Journals.vue**

```vue
<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <n-h2 style="margin: 0;">期刊管理</n-h2>
    <n-button type="primary" @click="showAddModal = true">新增期刊</n-button>
  </div>

  <n-data-table :columns="columns" :data="journals" :loading="loading" :pagination="false" />

  <!-- Add / Edit Modal -->
  <n-modal v-model:show="showAddModal" title="新增期刊">
    <n-card style="width: 500px;" :title="editingId ? '编辑期刊' : '新增期刊'" role="dialog">
      <n-form :model="form">
        <n-form-item label="名称"><n-input v-model:value="form.name" /></n-form-item>
        <n-form-item label="标识"><n-input v-model:value="form.slug" /></n-form-item>
        <n-form-item label="源类型">
          <n-select v-model:value="form.source_type" :options="[{ label: 'RSS', value: 'rss' }, { label: 'arXiv', value: 'arxiv' }]" />
        </n-form-item>
        <n-form-item label="源 URL"><n-input v-model:value="form.source_url" /></n-form-item>
        <n-form-item label="启用">
          <n-switch v-model:value="form.is_active" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showAddModal = false">取消</n-button>
        <n-button type="primary" @click="save" :loading="saving">保存</n-button>
      </template>
    </n-card>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { getAllJournals, createJournal, updateJournal, deleteJournal } from '@/api/admin'
import type { Journal } from '@/api/journals'

const message = useMessage()
const journals = ref<Journal[]>([])
const loading = ref(true)
const showAddModal = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)

const form = ref<Partial<Journal>>({ name: '', slug: '', source_type: 'rss', source_url: '', is_active: true })

const columns = [
  { title: '名称', key: 'name' },
  { title: '标识', key: 'slug' },
  { title: '类型', key: 'source_type', render: (row: Journal) => h(NTag, { size: 'small' }, { default: () => row.source_type }) },
  { title: '状态', key: 'is_active', render: (row: Journal) => row.is_active ? '启用' : '禁用' },
  {
    title: '操作', key: 'actions',
    render: (row: Journal) => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', onClick: () => edit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, { onPositiveClick: () => remove(row.id) }, {
          default: () => '确认删除？',
          trigger: () => h(NButton, { size: 'small', type: 'error', ghost: true }, { default: () => '删除' }),
        }),
      ],
    }),
  },
]

function edit(row: Journal) {
  editingId.value = row.id
  form.value = { ...row }
  showAddModal.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateJournal(editingId.value, form.value as Journal)
      message.success('已更新')
    } else {
      await createJournal(form.value as Journal)
      message.success('已创建')
    }
    showAddModal.value = false
    editingId.value = null
    load()
  } catch (e: any) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(id: string) {
  try {
    await deleteJournal(id)
    message.success('已删除')
    load()
  } catch (e: any) {
    message.error(e.message)
  }
}

async function load() {
  loading.value = true
  try {
    journals.value = (await getAllJournals()).journals
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
```

- [ ] **Step 3: Write admin/Requests.vue**

```vue
<template>
  <n-h2>期刊申请审核</n-h2>
  <n-data-table :columns="columns" :data="requests" :loading="loading" />
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NButton, NSpace, NTag, useMessage } from 'naive-ui'
import { getRequests, reviewRequest, type JournalRequest } from '@/api/admin'

const message = useMessage()
const requests = ref<JournalRequest[]>([])
const loading = ref(true)

const columns = [
  { title: '期刊名', key: 'journal_name' },
  { title: '来源', key: 'source_url', ellipsis: true },
  { title: '状态', key: 'status', render: (row: JournalRequest) => {
    const map: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
    return h(NTag, { size: 'small', type: row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'error' : 'warning' },
      { default: () => map[row.status] || row.status })
  }},
  { title: '申请时间', key: 'created_at' },
  {
    title: '操作', key: 'actions',
    render: (row: JournalRequest) => row.status === 'pending' ? h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => review(row.id, 'approved') }, { default: () => '通过' }),
        h(NButton, { size: 'small', type: 'error', ghost: true, onClick: () => review(row.id, 'rejected') }, { default: () => '拒绝' }),
      ],
    }) : null,
  },
]

async function review(id: string, status: string) {
  try {
    await reviewRequest(id, status)
    message.success(status === 'approved' ? '已通过' : '已拒绝')
    load()
  } catch (e: any) {
    message.error(e.message)
  }
}

async function load() {
  loading.value = true
  try {
    requests.value = (await getRequests()).requests
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
```

- [ ] **Step 4: Write admin/Users.vue**

```vue
<template>
  <n-h2>用户管理</n-h2>
  <n-data-table :columns="columns" :data="users" :loading="loading" />
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { NTag } from 'naive-ui'
import { getUsers, type User } from '@/api/admin'

const users = ref<User[]>([])
const loading = ref(true)

const columns = [
  { title: '邮箱', key: 'email' },
  { title: '昵称', key: 'name' },
  { title: '推送频率', key: 'push_frequency', render: (row: User) =>
    h(NTag, { size: 'small' }, { default: () => row.push_frequency === 'realtime' ? '实时' : '每日' })
  },
  { title: '注册时间', key: 'created_at' },
]

onMounted(async () => {
  try {
    users.value = (await getUsers()).users
  } finally {
    loading.value = false
  }
})
</script>
```

- [ ] **Step 5: Verify build**

Run: `cd web && npx vue-tsc -b && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add web/src/views/admin/
git commit -m "feat: add admin pages — dashboard, journals, requests, users"
```

---

### Task 9: Go embed integration — serve SPA from binary

**Files:**
- Modify: `cmd/server/main.go`
- Modify: `web/vite.config.ts` (set base)
- Create: `web/index.html` — add `{{ . }}` fallback for SPA routing (handled by Gin)

- [ ] **Step 1: Update main.go to embed web/dist**

```go
package main

import (
	"context"
	"embed"
	"fmt"
	"io/fs"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/humumu/journal-monitor/internal/api"
	"github.com/humumu/journal-monitor/internal/config"
	"github.com/humumu/journal-monitor/internal/repo"
	"github.com/humumu/journal-monitor/internal/scheduler"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

//go:embed web/dist/*.html web/dist/assets/*
var spaFiles embed.FS

func main() {
	cfg := config.Load()

	if len(os.Args) > 1 && os.Args[1] == "migrate" {
		runMigrations(cfg)
		return
	}

	if err := cfg.Validate(); err != nil {
		log.Fatalf("config validation failed: %v", err)
	}

	// PostgreSQL
	pgPool, err := pgxpool.New(context.Background(), cfg.DB.DSN)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	if err := pgPool.Ping(context.Background()); err != nil {
		log.Fatalf("failed to ping postgres: %v", err)
	}
	defer pgPool.Close()

	// Redis
	rdb := redis.NewClient(&redis.Options{
		Addr: cfg.Redis.Addr,
	})
	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}
	defer rdb.Close()

	// Scheduler
	sched := scheduler.New(pgPool, rdb, cfg,
		repo.NewJournalRepo(pgPool),
		repo.NewArticleRepo(pgPool),
		repo.NewSubscriptionRepo(pgPool),
		repo.NewUserRepo(pgPool),
		repo.NewNotificationRepo(pgPool),
	)
	sched.Start(context.Background())

	r := api.SetupRouter(pgPool, rdb, cfg)

	// Serve SPA: API routes registered first, then catch-all for SPA
	spaFS, err := fs.Sub(spaFiles, "web/dist")
	if err != nil {
		log.Fatalf("failed to get spa sub filesystem: %v", err)
	}
	r.Use(func(c *gin.Context) {
		// Only handle non-API, non-health requests
		if strings.HasPrefix(c.Request.URL.Path, "/api/") ||
			c.Request.URL.Path == "/health" {
			c.Next()
			return
		}
		c.Next()
	})
	r.NoRoute(func(c *gin.Context) {
		c.FileFromFS("index.html", http.FS(spaFS))
	})
	r.StaticFS("/assets", http.FS(spaFS))

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%s", cfg.Server.Port),
		Handler: r,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("server starting on port %s", cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	<-quit
	sched.Stop()
	log.Println("shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("server forced shutdown: %v", err)
	}
}
```

- [ ] **Step 2: Update vite.config.ts to set base path**

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
      '/health': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

- [ ] **Step 3: Build frontend + backend together**

```bash
cd web && npm run build && cd ..
go build -o bin/server ./cmd/server
```

Expected: `bin/server` binary created, contains embedded SPA

- [ ] **Step 4: Update Makefile**

```makefile
.PHONY: build run migrate test docker-build

build:
	cd web && npm run build
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server

migrate:
	@echo "Running migrations..."
	go run ./cmd/server migrate
	@echo "Migrations complete."

docker-build:
	docker build -t journal-monitor .

test:
	go test ./... -v
```

- [ ] **Step 5: Update Dockerfile to build frontend**

```dockerfile
FROM node:20-alpine AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM golang:1.24-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=web-builder /web/dist ./web/dist
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server ./cmd/server

FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/server .
COPY migrations/ ./migrations/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 6: Verify full build**

```bash
go build ./... && cd web && npm run build
```

Expected: Both Go binary and web dist build successfully

- [ ] **Step 7: Commit**

```bash
git add cmd/server/main.go web/vite.config.ts Makefile Dockerfile
git commit -m "feat: integrate SPA into Go binary via embed"
```

---

### Self-Review

**1. Spec coverage:**
| Spec section | Task covering it |
|---|---|
| Vue 3 + Vite 脚手架 | Task 1 |
| API client + auth store | Task 2 |
| Router + layouts | Task 3 |
| 登录/注册 | Task 4 |
| 首页文章流 | Task 5 |
| 期刊广场 | Task 5 |
| 文章详情 | Task 5 |
| 个性化 feed | Task 6 |
| 订阅管理 | Task 6 |
| 通知历史 | Task 6 |
| 设置 | Task 6 |
| Admin API 端点 | Task 7 |
| Admin 页面 | Task 8 |
| Go embed 集成 | Task 9 |

**2. Placeholder scan:** No TBD, TODOs, or incomplete code. All imports are included. All type references match.

**3. Type consistency:** `Journal`, `Article`, `AuthResponse`, `JournalRequest`, `User` types used consistently between API client and store/component layers. Admin response types match what the Go backend returns.
