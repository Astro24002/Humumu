<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'

onLaunch(() => {
  const auth = useAuthStore()
  auth.restore()
})
</script>

<style>
page { background-color: #f8f8f8; }
</style>
