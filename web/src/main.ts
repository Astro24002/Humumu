import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useAuthStore } from '@/stores/auth'

async function bootstrap() {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)

  // Refresh profile (is_admin etc.) from /auth/me when a token is present.
  const auth = useAuthStore()
  await auth.refreshMe()

  app.use(router)
  app.mount('#app')
}

bootstrap()
