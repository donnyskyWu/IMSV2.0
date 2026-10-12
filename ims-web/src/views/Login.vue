<script setup lang="ts">
/**
 * 账号密码登录（FP-B1-LG-01 / LG-02 / LG-03）
 * 本 PR 不做钉钉扫码，因此不显示 Tab，只保留账号登录。
 * 锁定倒计时、1216 / 1008 按错误码展示；次数与改密是否生效等后端第 2 个 PR 联调。
 */
import { computed, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FormField from '@/components/form/FormField.vue'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import { LOGIN_COPY, lockMessage, parseLockMinutes } from '@/utils/login-errors'
import { resolveLanding, sanitizeRedirect } from '@/utils/login-landing'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const usernameError = ref('')
const passwordError = ref('')
const banner = ref('')
const lockedUsername = ref('')
const remainMinutes = ref(0)
let lockTimer = 0

const loginDisabled = computed(() => {
  if (loading.value) return true
  if (!lockedUsername.value || remainMinutes.value <= 0) return false
  return username.value.trim() === lockedUsername.value
})

function stopLockCountdown() {
  if (lockTimer) {
    window.clearInterval(lockTimer)
    lockTimer = 0
  }
}

function startLockCountdown(name: string, minutes: number) {
  stopLockCountdown()
  lockedUsername.value = name
  remainMinutes.value = minutes
  banner.value = lockMessage(minutes)
  lockTimer = window.setInterval(() => {
    if (remainMinutes.value <= 1) {
      remainMinutes.value = 0
      lockedUsername.value = ''
      banner.value = ''
      stopLockCountdown()
      return
    }
    remainMinutes.value -= 1
    banner.value = lockMessage(remainMinutes.value)
  }, 60_000)
}

onUnmounted(stopLockCountdown)

function registeredPaths(): string[] {
  return router.getRoutes().map((item) => item.path).filter((path) => !path.includes(':'))
}

function goAfterLogin(pwdResetRequired: boolean) {
  const redirect = sanitizeRedirect(route.query.redirect)
  if (pwdResetRequired) {
    router.push({
      path: '/password-reset',
      query: redirect ? { redirect } : {},
    })
    return
  }
  router.push(resolveLanding({
    redirect,
    menus: authStore.menus,
    registeredPaths: registeredPaths(),
  }))
}

function trimUsername() {
  username.value = username.value.trim()
}

async function handleLogin() {
  if (loginDisabled.value) return
  trimUsername()
  usernameError.value = username.value ? '' : LOGIN_COPY.usernameRequired
  passwordError.value = password.value ? '' : LOGIN_COPY.passwordRequired
  if (usernameError.value || passwordError.value) return

  loading.value = true
  banner.value = ''
  try {
    const outcome = await authStore.login(username.value, password.value)
    if (outcome.ok) {
      stopLockCountdown()
      lockedUsername.value = ''
      goAfterLogin(outcome.pwdResetRequired)
      return
    }
    if (outcome.code === 1214) {
      password.value = ''
      passwordError.value = LOGIN_COPY.wrongPassword
      return
    }
    if (outcome.code === 1215) {
      startLockCountdown(username.value.trim(), parseLockMinutes(outcome.data, outcome.msg))
      return
    }
    if (outcome.code === 1216) {
      banner.value = LOGIN_COPY.frozen
      return
    }
    if (outcome.code === 1008) {
      banner.value = LOGIN_COPY.tenantDisabled
      return
    }
    if (outcome.code === -1) {
      toast.error(LOGIN_COPY.network)
      return
    }
    toast.error(LOGIN_COPY.busy)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-shell">
    <section class="login-brand">
      <h1 class="brand-name">IMS 内部管理系统</h1>
      <p class="brand-desc">使用账号密码进入系统</p>
    </section>

    <section class="login-panel">
      <div class="login-card" data-testid="login-card">
        <h2 class="login-title">登录</h2>
        <p
          v-if="banner"
          class="login-banner"
          role="alert"
          data-testid="login-banner"
        >
          {{ banner }}
        </p>

        <el-form @submit.prevent="handleLogin">
          <FormField label="用户名" required>
            <div class="field-block">
              <el-input
                v-model="username"
                placeholder="请输入用户名"
                autocomplete="username"
                @blur="trimUsername"
              />
              <p v-if="usernameError" class="field-error" role="alert">{{ usernameError }}</p>
            </div>
          </FormField>
          <FormField label="密码" required>
            <div class="field-block">
              <el-input
                v-model="password"
                type="password"
                placeholder="请输入密码"
                autocomplete="current-password"
                show-password
              />
              <p v-if="passwordError" class="field-error" role="alert">{{ passwordError }}</p>
            </div>
          </FormField>
          <el-button
            class="login-submit"
            type="primary"
            native-type="submit"
            :loading="loading"
            :disabled="loginDisabled"
          >
            登录
          </el-button>
        </el-form>
        <p class="login-foot">遇到问题请联系系统管理员</p>
      </div>
    </section>
  </div>
</template>

<style lang="scss" scoped>
.login-shell {
  min-height: 100vh;
  display: flex;
  background-color: var(--bg);
}

.login-brand {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px;
}

.brand-name {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
}

.brand-desc {
  margin: 0;
  font-size: 14px;
  color: var(--text2);
}

.login-panel {
  flex: 0 0 480px;
  width: 480px;
  max-width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.login-card {
  width: 400px;
  max-width: 100%;
  padding: 32px 28px 24px;
  background-color: var(--card);
  border-radius: var(--r);
  box-shadow: var(--sh);
}

.login-title {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.login-banner {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: var(--r-s);
  background-color: var(--status-danger-bg);
  color: var(--red);
  font-size: 13px;
  line-height: 1.5;
}

.field-block {
  width: 100%;
}

/* 标签在输入框上方，避免窄屏下和输入框叠在一起 */
:deep(.el-form-item) {
  display: block;
}

:deep(.el-form-item__label) {
  display: flex;
  width: 100% !important;
  height: auto;
  justify-content: flex-start;
  margin-bottom: 6px;
  padding: 0;
  line-height: 1.4;
  text-align: left;
}

:deep(.el-form-item__content) {
  display: block;
  width: 100%;
  margin-left: 0 !important;
}

:deep(.el-input) {
  width: 100%;
}

.field-error {
  margin: 6px 0 0;
  color: var(--red);
  font-size: 12px;
  line-height: 1.4;
}

.login-submit {
  width: 100%;
  min-height: 44px;
  margin-top: 4px;
}

.login-foot {
  margin: 16px 0 0;
  font-size: 12px;
  color: var(--text2);
  text-align: center;
}

@media (width <= 767px) {
  .login-shell {
    flex-direction: column;
  }

  .login-brand {
    flex: none;
    padding: 28px 16px 0;
  }

  .login-panel {
    flex: none;
    width: 100%;
  }

  .login-card {
    width: 100%;
  }

  .brand-name {
    font-size: 22px;
  }
}
</style>
