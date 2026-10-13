<script setup lang="ts">
/**
 * 待办中心 (B3-TD)
 * 依据: 个人工作台-实现理解 §4.2，UI 对齐 workbenchTodos 与产品复核。
 *
 * 功能:
 * - TD-01: 列表与筛选（默认待处理，已过期）
 * - TD-02: 排序与逾期高亮
 * - TD-03: 去处理（先 GET 确认仍为 PENDING）
 * - TD-04: 关闭待办
 * - TD-05: 待办计数
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import { todoApi, type TodoItem, type TodoCountResponse } from '@/api/workbench'
import { useTodoActions } from '@/composables/useTodoActions'
import {
  TODO_TABS,
  canCloseTodo,
  isTodoTabKey,
  overdueText,
  todoStatusText,
  todoTypeInfo,
} from '@/utils/todo-display'

const route = useRoute()

const loading = ref(false)
const todos = ref<TodoItem[]>([])
const total = ref(0)
const counts = ref<TodoCountResponse | null>(null)

const currentTab = ref<string>('all')
const currentStatus = ref<string>('PENDING')
const keyword = ref('')
const pageNo = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detailTodo = ref<TodoItem | null>(null)

const tabs = computed(() => {
  return TODO_TABS.map((tab) => ({
    ...tab,
    count: tab.key === 'all'
      ? counts.value?.total || 0
      : counts.value?.byType?.[tab.key] || 0,
  }))
})

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'PENDING', label: '待处理' },
  { value: 'OVERDUE', label: '已过期' },
  { value: 'DONE', label: '已处理' },
]

function formatDueTime(dueTime: string | null): string {
  if (!dueTime) return '-'
  const date = new Date(dueTime)
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function statusTagType(row: TodoItem): 'warning' | 'success' | 'danger' | 'info' {
  if (row.status === 'DONE') return 'success'
  if (row.isOverdue) return 'danger'
  if (row.status === 'PENDING') return 'warning'
  return 'info'
}

function showView(row: TodoItem): boolean {
  return row.status === 'DONE' || row.isOverdue
}

function showGo(row: TodoItem): boolean {
  return row.status === 'PENDING'
}

async function fetchData() {
  loading.value = true
  try {
    const [todosRes, countsRes] = await Promise.all([
      todoApi.getMyPage({
        type: currentTab.value === 'all' ? undefined : currentTab.value,
        status: currentStatus.value || undefined,
        keyword: keyword.value || undefined,
        pageNo: pageNo.value,
        pageSize: pageSize.value,
      }),
      todoApi.getMyCount(),
    ])

    if (todosRes.code === 0 && todosRes.data) {
      todos.value = todosRes.data.list
      total.value = todosRes.data.total
    }
    if (countsRes.code === 0 && countsRes.data) {
      counts.value = countsRes.data
    }
  } finally {
    loading.value = false
  }
}

const { handleGo, handleClose } = useTodoActions(fetchData)

function handleTabChange(key: string) {
  currentTab.value = key
  pageNo.value = 1
  fetchData()
}

function handleStatusChange() {
  pageNo.value = 1
  fetchData()
}

function handleSearch() {
  pageNo.value = 1
  fetchData()
}

function handleReset() {
  keyword.value = ''
  currentStatus.value = 'PENDING'
  pageNo.value = 1
  fetchData()
}

function handlePageChange(page: number) {
  pageNo.value = page
  fetchData()
}

function openDetail(row: TodoItem) {
  detailTodo.value = row
  detailVisible.value = true
}

function applyTabQuery(tab: unknown) {
  if (typeof tab === 'string' && isTodoTabKey(tab)) {
    currentTab.value = tab
  }
}

onMounted(() => {
  applyTabQuery(route.query.tab)
  fetchData()
})

watch(() => route.query.tab, (newTab) => {
  if (typeof newTab === 'string' && isTodoTabKey(newTab) && newTab !== currentTab.value) {
    currentTab.value = newTab
    pageNo.value = 1
    fetchData()
  }
})
</script>

<template>
  <AppLayout>
    <div class="todos-page">
      <PageHeader title="待办中心" />

      <div class="tabs-row">
        <el-radio-group v-model="currentTab" @change="handleTabChange">
          <el-radio-button v-for="tab in tabs" :key="tab.key" :value="tab.key">
            {{ tab.label }}
            <el-badge v-if="tab.count > 0" :value="tab.count" class="tab-badge" />
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="filter-row">
        <el-select v-model="currentStatus" placeholder="状态" style="width: 120px" @change="handleStatusChange">
          <el-option v-for="opt in statusOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="搜索标题或内容"
          style="width: 200px"
          clearable
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table :data="todos" v-loading="loading" style="width: 100%">
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="todoTypeInfo(row.type).type" size="small">
              {{ todoTypeInfo(row.type).text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sourceModule" label="来源" width="120" show-overflow-tooltip />
        <el-table-column label="截止时间" width="180">
          <template #default="{ row }">
            <span :class="{ 'overdue-text': row.isOverdue }">
              {{ formatDueTime(row.dueTime) }}
            </span>
            <span v-if="row.isOverdue" class="overdue-badge">{{ overdueText(true, row.overdueDays || 0) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row)" size="small">
              {{ todoStatusText(row.status, row.isOverdue) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="showView(row)" text type="primary" @click="openDetail(row)">
              查看
            </el-button>
            <el-button v-if="showGo(row)" text type="primary" @click="handleGo(row)">
              去处理
            </el-button>
            <el-button
              v-if="row.status === 'PENDING' && canCloseTodo(row.type)"
              text
              type="default"
              @click="handleClose(row)"
            >
              关闭
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span class="table-empty">暂无待办</span>
        </template>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="pageNo"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>

      <DetailDrawer v-model="detailVisible" :title="detailTodo?.title || '待办详情'">
        <div v-if="detailTodo" class="detail-body">
          <div class="detail-row">
            <span class="detail-label">类型</span>
            <span>{{ todoTypeInfo(detailTodo.type).text }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">状态</span>
            <span>{{ todoStatusText(detailTodo.status, detailTodo.isOverdue) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">来源</span>
            <span>{{ detailTodo.sourceModule || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">截止时间</span>
            <span>{{ formatDueTime(detailTodo.dueTime) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">内容</span>
            <span>{{ detailTodo.content || '-' }}</span>
          </div>
          <div v-if="detailTodo.doneByName" class="detail-row">
            <span class="detail-label">处理人</span>
            <span>{{ detailTodo.doneByName }}</span>
          </div>
        </div>
      </DetailDrawer>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.todos-page {
  width: 100%;
}

.tabs-row {
  margin-bottom: 16px;
  max-width: 100%;
  overflow-x: auto;

  :deep(.el-radio-button__inner) {
    position: relative;
    padding-right: 24px;
  }
}

.tab-badge {
  position: absolute;
  top: -8px;
  right: -8px;

  :deep(.el-badge__content) {
    font-size: 10px;
    padding: 0 4px;
    height: 16px;
    line-height: 16px;
  }
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.overdue-text {
  color: var(--danger);
}

.overdue-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 0 6px;
  font-size: 11px;
  background-color: var(--danger);
  color: #fff;
  border-radius: 2px;
}

.table-empty {
  color: var(--text2);
  font-size: 14px;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  gap: 12px;
  font-size: 14px;
  color: var(--text);
}

.detail-label {
  flex: none;
  width: 72px;
  color: var(--text2);
}
</style>
