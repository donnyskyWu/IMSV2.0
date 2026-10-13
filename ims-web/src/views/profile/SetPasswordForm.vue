<script setup lang="ts">
/**
 * 个人中心「设置密码」（FP-B2-PC-03）
 * 没有当前密码。成功后本页改成修改密码。
 */
import { ref } from 'vue'
import FormField from '@/components/form/FormField.vue'
import { setPassword } from '@/api/profile'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import { LOGIN_COPY } from '@/utils/login-errors'
import {
  PASSWORD_COPY,
  hasPasswordErrors,
  validatePasswordChange,
} from '@/utils/password-rules'

const emit = defineEmits<{ success: [] }>()
const authStore = useAuthStore()

const newPassword = ref('')
const confirmPassword = ref('')
const saving = ref(false)
const newError = ref('')
const confirmError = ref('')

function applyErrors() {
  const errors = validatePasswordChange({
    oldPassword: ' ',
    newPassword: newPassword.value,
    confirmPassword: confirmPassword.value,
  })
  newError.value = errors.newPassword || ''
  confirmError.value = errors.confirmPassword || ''
  return errors
}

async function handleSubmit() {
  if (saving.value) return
  const errors = applyErrors()
  if (errors.newPassword || errors.confirmPassword) return
  if (hasPasswordErrors({ newPassword: newError.value, confirmPassword: confirmError.value })) return

  saving.value = true
  try {
    await setPassword(newPassword.value)
    toast.success('密码已设置')
    if (authStore.user) {
      authStore.user = { ...authStore.user, hasPassword: true }
    }
    emit('success')
  } catch (err) {
    if (err instanceof ApiError && err.code === 1001) {
      newError.value = err.message || PASSWORD_COPY.rule
      return
    }
    if (err instanceof ApiError && err.code === -1) {
      toast.error(LOGIN_COPY.network)
      return
    }
    toast.error(LOGIN_COPY.busy)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-form class="auth-form" data-testid="password-set-form" @submit.prevent="handleSubmit">
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
    <el-button class="pwd-submit" type="primary" native-type="submit" :loading="saving" :disabled="saving">
      设置密码
    </el-button>
  </el-form>
</template>

<style lang="scss" scoped>
.field-block {
  width: 100%;
}

.field-error {
  margin: 6px 0 0;
  color: var(--red);
  font-size: 12px;
  line-height: 1.4;
}

.pwd-submit {
  min-height: 44px;
}
</style>
