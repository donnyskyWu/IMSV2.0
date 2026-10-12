<script setup lang="ts">
/**
 * 登录页占位
 * 登录页归 B1 批次，B0b 只提供跳转
 */
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('qa_admin')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    const ok = await authStore.login(username.value, password.value)
    if (!ok) {
      ElMessage.error('用户名或密码错误')
      return
    }
    if (sessionStorage.getItem('ims_pwd_reset') === '1' || authStore.pwdResetRequired) {
      router.push('/user/change-password')
      return
    }
    const redirect = (route.query.redirect as string) || '/demo/tokens'
    router.push(redirect)
  } catch {
    ElMessage.error('用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">IMS 登录</h1>
      <p class="login-subtitle">登录页归 B1 批次，此为占位页</p>

      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            show-password
          />
        </el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          style="width: 100%"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 360px;
  padding: 32px;
  background-color: var(--card);
  border-radius: var(--r);
  box-shadow: var(--sh);
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  text-align: center;
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 13px;
  color: var(--text2);
  text-align: center;
  margin: 0 0 24px;
}
</style>
