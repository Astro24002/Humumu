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
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/Dashboard.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
        { path: 'journals', name: 'AdminJournals', component: () => import('@/views/admin/Journals.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
        { path: 'requests', name: 'AdminRequests', component: () => import('@/views/admin/Requests.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
        { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
      ],
    },
  ],
})

router.beforeEach((to, _from) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'Home' }
  }
})

export default router
