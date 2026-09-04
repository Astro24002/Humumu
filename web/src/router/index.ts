import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    // Restore scroll on browser back/forward; otherwise jump to top.
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      component: DefaultLayout,
      children: [
        { path: '', name: 'Home', component: () => import('@/views/Home.vue'), meta: { title: '公开广场' } },
        { path: 'journals', name: 'Journals', component: () => import('@/views/Journals.vue'), meta: { title: '期刊广场' } },
        { path: 'journals/:id', name: 'JournalDetail', component: () => import('@/views/JournalDetail.vue'), meta: { title: '期刊详情' } },
        { path: 'articles/:id', name: 'ArticleDetail', component: () => import('@/views/ArticleDetail.vue'), meta: { title: '论文详情' } },
        { path: 'login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { title: '登录' } },
        { path: 'register', name: 'Register', component: () => import('@/views/Register.vue'), meta: { title: '注册' } },
        { path: 'my', name: 'MyFeed', component: () => import('@/views/my/Feed.vue'), meta: { requiresAuth: true, title: '我的更新' } },
        { path: 'my/subscriptions', name: 'MySubscriptions', component: () => import('@/views/my/Subscriptions.vue'), meta: { requiresAuth: true, title: '订阅管理' } },
        { path: 'my/notifications', name: 'MyNotifications', component: () => import('@/views/my/Notifications.vue'), meta: { requiresAuth: true, title: '通知历史' } },
        { path: 'settings', name: 'Settings', component: () => import('@/views/Settings.vue'), meta: { requiresAuth: true, title: '个人设置' } },
        { path: ':pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
      ],
    },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '管理概览' } },
        { path: 'journals', name: 'AdminJournals', component: () => import('@/views/admin/Journals.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '期刊管理' } },
        { path: 'categories', name: 'AdminCategories', component: () => import('@/views/admin/Categories.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: 'CAS 分类' } },
        { path: 'requests', name: 'AdminRequests', component: () => import('@/views/admin/Requests.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '申请审核' } },
        { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '用户管理' } },
      ],
    },
  ],
})

router.beforeEach((to, _from) => {
  const auth = useAuthStore()
  const needsAuth = to.matched.some((r) => r.meta.requiresAuth)
  const needsAdmin = to.matched.some((r) => r.meta.requiresAdmin)
  if (needsAuth && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (needsAdmin && !auth.isAdmin) {
    // Logged-in non-admins land on personal home, not the public plaza.
    return auth.isLoggedIn ? { name: 'MyFeed' } : { name: 'Home' }
  }
})

router.afterEach((to, from) => {
  // Keep detail-page dynamic titles when only the query (e.g. ?page=) changes.
  if (
    to.name === from.name
    && to.params
    && from.params
    && JSON.stringify(to.params) === JSON.stringify(from.params)
    && (to.name === 'JournalDetail' || to.name === 'ArticleDetail')
  ) {
    return
  }
  const pageTitle = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = pageTitle ? `${pageTitle} · Humumu` : 'Humumu'
})

export default router
