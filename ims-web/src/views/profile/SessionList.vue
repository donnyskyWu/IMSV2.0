<script setup lang="ts">
/**
 * 我的会话（FP-B2-PC-04）
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteMySession, listMySessions, type SessionItem } from '@/api/profile'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'

const router = useRouter()
const authStore = useAuthStore()
const rows = ref<SessionItem[]>([])
const loading = ref(false)
const errorText = ref('')

async function load() {
  loading.value = true
  errorText.value = ''
  try {
    const result = await listMySessions()
    rows.value = result.data?.list || []
  } catch (err) {
    errorText.value = err instanceof ApiError ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function kick(row: SessionItem) {
  try {
    await deleteMySession(row.sid)
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : '操作失败')
    return
  }
  if (row.current) {
    authStore.clearSession()
    await router.replace('/login')
    return
  }
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="session-list">
    <p v-if="errorText" role="alert">{{ errorText }}</p>
    <el-table v-loading="loading" :data="rows" row-key="sid">
      <el-table-column prop="deviceName" label="设备" />
      <el-table-column prop="ip" label="IP" />
      <el-table-column prop="loginTime" label="登录时间" />
      <el-table-column prop="lastActiveTime" label="最后活跃" />
      <el-table-column label="当前">
        <template #default="{ row }">
          <span v-if="row.current">当前</span>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button
            v-if="!row.current"
            link
            type="primary"
            :data-sid="row.sid"
            @click="kick(row)"
          >
            下线
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
