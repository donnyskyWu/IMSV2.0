<script setup lang="ts">
/**
 * 强制改密（FP-B1-PW-01）
 * 无侧栏。校验在前端完成；提交走改密适配层，接口未返回成功时不离开本页。
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FormField from '@/components/form/FormField.vue'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import { LOGIN_COPY } from '@/utils/login-errors'
import { resolveLanding, sanitizeRedirect } from '@/utils/login-landing'
import {
  PASSWORD_COPY,
  hasPasswordErrors,
  validatePasswordChange,
} from '@/utils/password-rules'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const saving = ref(false)
const oldError = ref('')
const newError = ref('')
const confirmError = ref('')

function registeredPaths(): string[] {
  return router.getRoutes().map((item) => item.path).filter((path) => !path.includes(':'))
}

function applyErrors() {
  const errors = validatePasswordChange({
    oldPassword: oldPassword.value,
    newPassword: newPassword.value,
    confirmPassword: confirmPassword.value,
  })
  oldError.value = errors.oldPassword || ''
  newError.value = errors.newPassword || ''
  confirmError.value = errors.confirmPassword || ''
  return errors
}

async function handleSubmit() {
  if (saving.value) return
  const errors = applyErrors()
  if (hasPasswordErrors(errors)) return

  saving.value = true
  oldError.value = ''
  try {
    const outcome = await authStore.submitPasswordChange(oldPassword.value, newPassword.value)
    if (!outcome.ok) {
      if (outcome.code === 1214) {
        oldError.value = PASSWORD_COPY.wrongOld
        return
      }
      if (outcome.code === 1001) {
        newError.value = PASSWORD_COPY.rule
        return
      }
      if (outcome.code === -1) {
        toast.error(LOGIN_COPY.network)
        return
      }
      toast.error(LOGIN_COPY.busy)
      return
    }
    if (outcome.pwdResetRequired) return
    toast.success(PASSWORD_COPY.updated)
    const redirect = sanitizeRedirect(route.query.redirect)
    await router.push(resolveLanding({
      redirect,
      menus: authStore.menus,
      registeredPaths: registeredPaths(),
    }))
  } finally {
    saving.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="pwd-page">
    <div class="pwd-card" data-testid="password-card">
      <div class="pwd-toolbar">
        <button type="button" class="logout-link" @click="handleLogout">退出登录</button>
      </div>
      <h1 class="pwd-title">请先修改密码</h1>
      <p class="pwd-desc">管理员已为您重置密码，为了账号安全，请设置新密码后继续使用</p>

      <el-form @submit.prevent="handleSubmit">
        <FormField label="当前密码" required>
          <div class="field-block">
            <el-input
              v-model="oldPassword"
              type="password"
              placeholder="请输入当前密码"
              autocomplete="current-password"
              show-password
            />
            <p v-if="oldError" class="field-error" role="alert">{{ oldError }}</p>
          </div>
        </FormField>
        <FormField label="新密码" required>
          <div class="field-block">
            <el-input
              v-model="newPassword"
              type="password"
              placeholder="请输入新密码"
              maxlength="32"
              autocomplete="new-password"
              show-password
            />
            <p v-if="newError" class="field-error" role="alert">{{ newError }}</p>
          </div>
        </FormField>
        <FormField label="确认新密码" required>
          <div class="field-block">
            <el-input
              v-model="confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              maxlength="32"
              autocomplete="new-password"
              show-password
            />
            <p v-if="confirmError" class="field-error" role="alert">{{ confirmError }}</p>
          </div>
        </FormField>
        <el-button
          class="pwd-submit"
          type="primary"
          native-type="submit"
          :loading="saving"
          :disabled="saving"
        >
          确认修改
        </el-button>
      </el-form>
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
  width: 100%;
  max-width: 400px;
  padding: 20px 28px 28px;
  background-color: var(--card);
  border-radius: var(--r);
  box-shadow: var(--sh);
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

.field-block {
  width: 100%;
}

:deep(.el-form-item__label) {
  display: flex;
  justify-content: flex-start;
  height: auto;
  margin-bottom: 6px;
  line-height: 1.4;
}

:deep(.el-form-item__content) {
  width: 100%;
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

.pwd-submit {
  width: 100%;
  min-height: 44px;
}
</style>
