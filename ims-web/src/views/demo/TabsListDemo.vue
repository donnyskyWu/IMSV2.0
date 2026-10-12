<script setup lang="ts">
/**
 * 标签列表演示页 (FP-P-06)
 * 依据: UI-L08
 * 包含: 标签页 + 列表
 */
import { ref, computed } from 'vue'
import StatCard from '@/components/list/StatCard.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Tabs from '@/components/layout/Tabs.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'

// 标签页
const activeTab = ref('all')
const tabs = [
  { name: 'all', label: '全部', count: 128 },
  { name: 'pending', label: '待处理', count: 23 },
  { name: 'processing', label: '处理中', count: 15 },
  { name: 'completed', label: '已完成', count: 85 },
  { name: 'closed', label: '已关闭', count: 5 },
]

// 模拟工单数据
const mockTickets = Array.from({ length: 128 }, (_, i) => ({
  id: String(i + 1),
  title: `工单 ${String(i + 1).padStart(4, '0')}：${['系统问题', '权限申请', '数据修改', '功能咨询', '其他'][i % 5]}`,
  priority: ['LOW', 'MEDIUM', 'HIGH', 'URGENT'][i % 4],
  status: ['pending', 'processing', 'completed', 'closed'][(i + Math.floor(i / 10)) % 4],
  creator: ['张三', '李四', '王五', '赵六'][i % 4],
  assignee: ['技术支持', '运维团队', '开发团队'][i % 3],
  createTime: `2026-10-${String((i % 28) + 1).padStart(2, '0')} ${String((i % 12) + 8).padStart(2, '0')}:00`,
}))

// 分页
const pageNo = ref(1)
const pageSize = ref(10)
const tabKeyword = ref<Record<string, string>>({ all: '', pending: '', processing: '', completed: '', closed: '' })
const keyword = computed({
  get: () => tabKeyword.value[activeTab.value] || '',
  set: (value: string) => {
    tabKeyword.value = { ...tabKeyword.value, [activeTab.value]: value }
  },
})
const stats = [
  { title: '今日工单', value: 12, ratio: 3.2 },
  { title: '超时', value: 2, ratio: -1.5 },
  { title: '完成', value: 8, ratio: 0.4 },
  { title: '待办', value: 4, ratio: 1 },
]

// 按标签过滤
const filteredTickets = computed(() => {
  let data = activeTab.value === 'all'
    ? mockTickets
    : mockTickets.filter((t) => t.status === activeTab.value)
  const q = tabKeyword.value[activeTab.value]
  if (q) data = data.filter((t) => t.title.includes(q))
  return data
})

const total = computed(() => filteredTickets.value.length)

const tableData = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filteredTickets.value.slice(start, start + pageSize.value)
})

// 切换标签
function handleTabChange() {
  pageNo.value = 1
}
</script>

<template>
  <AppLayout>
    <div class="tabs-list-demo">
      <PageHeader title="标签列表演示" sub-title="FP-P-06 / UI-L08">
        <template #actions>
          <el-button type="primary">新建工单</el-button>
        </template>
        <template #primary-action>
          <el-button type="primary">新建</el-button>
        </template>
      </PageHeader>

      <!-- 标签页 -->
      <StatCard :items="stats" :cols="4" />
      <Tabs
        v-model:active="activeTab"
        :items="tabs.map((tab) => ({ key: tab.name, label: tab.label, count: tab.count }))"
        @change="handleTabChange"
      />
      <el-input v-model="keyword" class="tab-keyword" placeholder="本页条件" @change="pageNo = 1" />

      <!-- 表格 -->
      <div class="table-wrap">
        <el-table :data="tableData" style="width: 100%">
          <el-table-column prop="id" label="工单号" width="100">
            <template #default="{ row }">
              <span class="mono">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="100">
            <template #default="{ row }">
              <StatusTag dict-type="ticket_priority" :value="row.priority" />
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <StatusTag dict-type="ticket_status" :value="row.status" />
            </template>
          </el-table-column>
          <el-table-column prop="creator" label="创建人" width="100" />
          <el-table-column prop="assignee" label="处理方" width="120" />
          <el-table-column prop="createTime" label="创建时间" width="160" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default>
              <el-button text type="primary" size="small">查看</el-button>
              <el-button text type="primary" size="small">处理</el-button>
            </template>
          </el-table-column>
        </el-table>

        <EmptyState v-if="tableData.length === 0" type="empty" />
      </div>

      <!-- 分页 -->
      <Pagination
        v-model:page-no="pageNo"
        v-model:page-size="pageSize"
        :total="total"
      />
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.tabs-list-demo {
  width: 100%;
}

.table-wrap {
  margin-top: 16px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
}
</style>
