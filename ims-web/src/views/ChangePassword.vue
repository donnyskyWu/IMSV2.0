<script setup lang="ts">
/**
 * 强制改密（FP-B1-PW-01）
 * 无侧栏。表单是 PasswordChangeForm，本页只负责说明和成功后的跳转。
 */
import { useRoute, useRouter } from 'vue-router'
import PasswordChangeForm from '@/components/password/PasswordChangeForm.vue'
import { useAuthStore } from '@/stores/auth'
import { landingPath, sanitizeRedirect } from '@/utils/login-landing'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

function registeredPaths(): string[] {
  return router.getRoutes().map((item) => item.path).filter((path) => !path.includes(':'))
}

async function handleSuccess() {
  const redirect = sanitizeRedirect(route.query.redirect)
  await router.push(landingPath({
    redirect,
    menus: authStore.menus,
    registeredPaths: registeredPaths(),
  }))
}

async function handleLogout() {
  await authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="pwd-page">
    <div class="pwd-card auth-card" data-testid="password-card">
      <div class="pwd-toolbar">
        <button type="button" class="logout-link" @click="handleLogout">退出登录</button>
      </div>
      <h1 class="pwd-title">请先修改密码</h1>
      <p class="pwd-desc">管理员已为您重置密码，为了账号安全，请设置新密码后继续使用</p>
      <PasswordChangeForm @success="handleSuccess" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.pwd-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background-color: var(--bg);
}

.pwd-card {
  padding: 20px 28px 28px;
}

.pwd-toolbar {
  display: flex;
  justify-content: flex-end;
}

.logout-link {
  min-width: 44px;
  min-height: 44px;
  padding: 0 4px;
  border: 0;
  background: transparent;
  color: var(--blue);
  font-size: 14px;
  cursor: pointer;
}

.pwd-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.pwd-desc {
  margin: 0 0 20px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text2);
}
</style>
