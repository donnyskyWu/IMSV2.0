<script setup lang="ts">
/** 通知记录（FP-B2-N） */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import { systemAdminApi } from '@/api/system-admin'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const status = ref('FAILED')
const rows = ref<Record<string, unknown>[]>([])
const columns: TableColumn[] = [
  { key: 'eventText', label: '事件类型' },
  { key: 'bizKey', label: '业务键' },
  { key: 'receiverName', label: '接收人' },
  { key: 'channelText', label: '渠道' },
  { key: 'statusText', label: '状态' },
  { key: 'createTime', label: '时间' },
  { key: 'actions', label: '操作' },
]

async function load() {
  const page = await systemAdminApi.notifyPage({ status: status.value, pageNo: 1, pageSize: 20 })
  rows.value = (page.list || []).map((row) => ({
    ...row,
    eventText: row.eventText || row.eventType,
    statusText: row.statusText || row.status,
    channelText: row.channelText || row.channel,
  }))
}

async function resend(row: Record<string, unknown>) {
  await systemAdminApi.notifyResend(String(row.id))
  toast.success('已补发')
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="page-notify">
    <PageHeader title="通知" />
    <select v-model="status" data-testid="notify-status" @change="load">
      <option value="FAILED">失败</option>
      <option value="SKIPPED">去重跳过</option>
      <option value="SENT">已发送</option>
    </select>
    <PlainTable :columns="columns" :data="rows">
      <template #cell-actions="{ row }">
        <el-button v-if="row.status === 'FAILED'" data-testid="btn-resend" @click="resend(row)">补发</el-button>
      </template>
    </PlainTable>
  </div>
</template>
