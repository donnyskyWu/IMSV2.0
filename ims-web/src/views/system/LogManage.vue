<script setup lang="ts">
/** 日志（FP-B2-L） */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import { systemAdminApi } from '@/api/system-admin'
import { useDownloadStore } from '@/stores/download'
import type { TableColumn } from '@/types'

const tab = ref<'operate' | 'login'>('operate')
const rows = ref<Record<string, unknown>[]>([])
const detail = ref<Record<string, unknown> | null>(null)
const result = ref('')
const downloadStore = useDownloadStore()

const operateColumns: TableColumn[] = [
  { key: 'createTime', label: '时间' },
  { key: 'operatorName', label: '操作人' },
  { key: 'module', label: '模块' },
  { key: 'operation', label: '操作' },
  { key: 'result', label: '结果' },
  { key: 'ip', label: 'IP' },
  { key: 'actions', label: '操作' },
]
const loginColumns: TableColumn[] = [
  { key: 'createTime', label: '时间' },
  { key: 'username', label: '用户名' },
  { key: 'loginMethod', label: '登录方式' },
  { key: 'result', label: '结果' },
  { key: 'ip', label: 'IP' },
]

async function load() {
  if (tab.value === 'operate') {
    const page = await systemAdminApi.operateLogPage({ pageNo: 1, pageSize: 20 })
    rows.value = page.list || []
  } else {
    const page = await systemAdminApi.loginLogPage({ pageNo: 1, pageSize: 20, result: result.value })
    rows.value = page.list || []
  }
}

async function openDetail(row: Record<string, unknown>) {
  detail.value = await systemAdminApi.operateLogDetail(String(row.id))
}

async function exportLogs() {
  const exported = await systemAdminApi.logExport(tab.value)
  downloadStore.start(tab.value === 'operate' ? '操作日志.csv' : '登录日志.csv')
  downloadStore.tasks[0].progress = 100
  downloadStore.tasks[0].status = 'completed'
  void exported
}

onMounted(load)
</script>

<template>
  <div data-testid="page-log">
    <PageHeader title="日志" />
    <div class="toolbar">
      <button type="button" data-testid="tab-operate" @click="tab = 'operate'; load()">操作日志</button>
      <button type="button" data-testid="tab-login" @click="tab = 'login'; load()">登录日志</button>
      <input v-if="tab === 'login'" v-model="result" data-testid="login-result" placeholder="结果" />
      <el-button data-testid="btn-log-query" @click="load">查询</el-button>
      <el-button data-testid="btn-log-export" @click="exportLogs">导出</el-button>
    </div>
    <PlainTable :columns="tab === 'operate' ? operateColumns : loginColumns" :data="rows">
      <template v-if="tab === 'operate'" #cell-actions="{ row }">
        <el-button data-testid="btn-log-detail" @click="openDetail(row)">详情</el-button>
      </template>
    </PlainTable>
    <aside v-if="detail" data-testid="log-detail">
      <p>{{ detail.requestMethod }} {{ detail.requestPath }}</p>
    </aside>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
