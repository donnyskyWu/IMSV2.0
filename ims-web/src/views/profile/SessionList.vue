<script setup lang="ts">
/**
 * 我的会话（FP-B2-PC-04）
 * 复用 DataTable。非当前会话才能下线。
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DataTable from '@/components/list/DataTable.vue'
import { deleteMySession, listMySessions, type SessionItem } from '@/api/profile'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const rows = ref<SessionItem[]>([])
const loading = ref(false)
const errorText = ref('')

const columns: TableColumn[] = [
  { key: 'deviceName', label: '设备' },
  { key: 'ip', label: 'IP' },
  { key: 'loginTime', label: '登录时间', type: 'time' },
  { key: 'lastActiveTime', label: '最后活跃', type: 'time' },
  { key: 'current', label: '当前' },
]

const tableRows = ref<Record<string, unknown>[]>([])

async function load() {
  loading.value = true
  errorText.value = ''
  try {
    const result = await listMySessions()
    rows.value = result.data?.list || []
    tableRows.value = rows.value.map((row) => ({ ...row }))
  } catch (err) {
    errorText.value = err instanceof ApiError ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function kick(row: Record<string, unknown>) {
  const sid = String(row.sid || '')
  try {
    await deleteMySession(sid)
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
    <DataTable :columns="columns" :data="tableRows" row-key="sid" :loading="loading">
      <template #cell-current="{ row }">
        <span v-if="row.current">当前</span>
      </template>
      <template #actions="{ row }">
        <el-button v-if="!row.current" link type="primary" @click="kick(row)">下线</el-button>
      </template>
    </DataTable>
  </div>
</template>
