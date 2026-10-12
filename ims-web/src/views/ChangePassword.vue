<script setup lang="ts">
/**
 * 修改密码占位 (FP-R-04)
 * 密码被重置后只能停留在此页，改密成功后恢复正常导航。
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'

const router = useRouter()
const authStore = useAuthStore()
const password = ref('')
const saving = ref(false)

async function handleSubmit() {
  if (password.value.length < 6) {
    toast.warning('密码至少 6 位')
    return
  }
  saving.value = true
  try {
    authStore.clearPwdReset()
    toast.success('密码已更新')
    router.push('/demo/tokens')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="change-password">
      <h1>修改密码</h1>
      <p>管理员已重置密码，请先修改密码后再使用其他功能。</p>
      <el-form @submit.prevent="handleSubmit">
        <el-form-item label="新密码">
          <el-input v-model="password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确认修改</el-button>
      </el-form>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.change-password {
  max-width: 420px;
  padding: 24px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
}
</style>
