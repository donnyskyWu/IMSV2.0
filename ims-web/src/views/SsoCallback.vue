<script setup lang="ts">
/**
 * 钉钉回调落地（B0b）。读 URL 片段里的令牌后立刻清掉片段。
 * 个人中心 E2E 用它接 mock 登录，不在这里做扫码。
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { setAccessToken, setRefreshToken } from '@/api/request'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const failed = ref(false)

onMounted(async () => {
  const raw = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash
  const params = new URLSearchParams(raw)
  const accessToken = params.get('accessToken') || ''
  const refreshToken = params.get('refreshToken') || ''
  const redirect = params.get('redirect') || '/profile'
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
  if (!accessToken) {
    failed.value = true
    await router.replace('/login')
    return
  }
  setAccessToken(accessToken)
  if (refreshToken) setRefreshToken(refreshToken)
  authStore.adoptSession()
  try {
    await authStore.fetchUserInfo()
  } catch {
    // 令牌已写入。/me 失败时后续请求再处理。
  }
  const target = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/profile'
  await router.replace(target)
})
</script>

<template>
  <p>正在登录…</p>
</template>
