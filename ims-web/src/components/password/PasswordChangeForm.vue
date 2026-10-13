<script setup lang="ts">
/**
 * 改密表单（FP-B1-PW-01 / FP-B2-PC-02）
 * 强制改密页和个人中心「修改密码」共用这一份，不复制校验。
 */
import { ref } from 'vue'
import FormField from '@/components/form/FormField.vue'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import { LOGIN_COPY } from '@/utils/login-errors'
import {
  PASSWORD_COPY,
  hasPasswordErrors,
  validatePasswordChange,
} from '@/utils/password-rules'

withDefaults(defineProps<{ submitLabel?: string }>(), { submitLabel: '确认修改' })

const emit = defineEmits<{ success: [] }>()
const authStore = useAuthStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const saving = ref(false)
const oldError = ref('')
const newError = ref('')
const confirmError = ref('')

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
    emit('success')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-form class="auth-form" data-testid="password-change-form" @submit.prevent="handleSubmit">
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
      {{ submitLabel }}
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
  width: 100%;
  min-height: 44px;
}
</style>
