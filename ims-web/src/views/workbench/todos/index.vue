<script setup lang="ts">
/**
 * 待办中心 (B3-TD)
 * 依据: 个人工作台-实现理解 §4.2
 *
 * 功能:
 * - TD-01: 列表与筛选
 * - TD-02: 排序与逾期高亮
 * - TD-03: 去处理
 * - TD-04: 关闭待办
 * - TD-05: 待办计数
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { todoApi, type TodoItem, type TodoCountResponse } from '@/api/workbench'
import { useAuthStore } from '@/stores/auth'
import { isRouteAccessible } from '@/utils/route-accessible'
import { ApiError } from '@/api/request'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const todos = ref<TodoItem[]>([])
const total = ref(0)
const counts = ref<TodoCountResponse | null>(null)

const currentTab = ref<string>('all')
const currentStatus = ref<string>('')
const keyword = ref('')
const pageNo = ref(1)
const pageSize = ref(20)

const tabs = computed(() => {
  const items = [
    { key: 'all', label: '全部', count: counts.value?.total || 0 },
    { key: 'APPROVAL', label: '审批', count: counts.value?.byType?.APPROVAL || 0 },
    { key: 'RETURN', label: '归还', count: counts.value?.byType?.RETURN || 0 },
    { key: 'REVIEW', label: '审核', count: counts.value?.byType?.REVIEW || 0 },
    { key: 'CONFIRM', label: '确认', count: counts.value?.byType?.CONFIRM || 0 },
    { key: 'WARNING', label: '预警', count: counts.value?.byType?.WARNING || 0 },
    { key: 'ALERT', label: '告警', count: counts.value?.byType?.ALERT || 0 },
  ]
  return items.filter((item) => item.key === 'all' || item.count > 0)
})

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'PENDING', label: '待处理' },
  { value: 'OVERDUE', label: '已逾期' },
  { value: 'DONE', label: '已处理' },
]

const typeLabels: Record<string, { text: string; type: 'primary' | 'warning' | 'info' | 'success' | 'danger' | '' }> = {
  APPROVAL: { text: '审批', type: 'primary' },
  RETURN: { text: '归还', type: 'warning' },
  REVIEW: { text: '审核', type: 'info' },
  CONFIRM: { text: '确认', type: 'success' },
  WARNING: { text: '预警', type: 'warning' },
  ALERT: { text: '告警', type: 'danger' },
  STUDY: { text: '学习', type: '' },
}

function getTypeInfo(type: string | null) {
  return typeLabels[type || ''] || { text: type || '待办', type: '' }
}

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

function getOverdueText(todo: TodoItem): string {
  if (!todo.isOverdue) return ''
  const days = todo.overdueDays || 0
  if (days === 0) return '已逾期'
  return `逾期 ${days} 天`
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
  currentStatus.value = ''
  pageNo.value = 1
  fetchData()
}

function handlePageChange(page: number) {
  pageNo.value = page
  fetchData()
}

async function handleGo(todo: TodoItem) {
  if (!todo.route) {
    ElMessage.info('暂无跳转目标')
    return
  }

  if (!isRouteAccessible(todo.route, authStore.menus)) {
    ElMessage.warning('暂无权限访问')
    return
  }

  try {
    await router.push(todo.route)
  } catch (err) {
    if (err instanceof ApiError && err.code === 1504) {
      ElMessage.warning('单据已被处理或删除')
    }
  }
}

async function handleClose(todo: TodoItem) {
  if (todo.type === 'APPROVAL' || todo.type === 'REVIEW') {
    ElMessage.warning('该待办需在来源单据中处理')
    return
  }

  try {
    await ElMessageBox.confirm('确定关闭该待办吗？关闭后将不再显示。', '提示', {
      confirmButtonText: '关闭',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const res = await todoApi.close(todo.id)
    if (res.code === 0) {
      ElMessage.success('待办已关闭')
      fetchData()
    }
  } catch (err) {
    if (err === 'cancel') return
    if (err instanceof ApiError) {
      if (err.code === 1001) {
        ElMessage.warning(err.message)
      }
    }
  }
}

onMounted(() => {
  const tabFromQuery = route.query.tab as string
  if (tabFromQuery && tabs.value.some((t) => t.key === tabFromQuery)) {
    currentTab.value = tabFromQuery
  }
  fetchData()
})

watch(() => route.query.tab, (newTab) => {
  if (newTab && typeof newTab === 'string') {
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

      <!-- Tab 切换 -->
      <div class="tabs-row">
        <el-radio-group v-model="currentTab" @change="handleTabChange">
          <el-radio-button v-for="tab in tabs" :key="tab.key" :value="tab.key">
            {{ tab.label }}
            <el-badge v-if="tab.count > 0" :value="tab.count" class="tab-badge" />
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 筛选栏 -->
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

      <!-- 列表 -->
      <el-table :data="todos" v-loading="loading" style="width: 100%">
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeInfo(row.type).type" size="small">
              {{ getTypeInfo(row.type).text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sourceModule" label="来源" width="120" show-overflow-tooltip />
        <el-table-column label="截止时间" width="160">
          <template #default="{ row }">
            <span :class="{ 'overdue-text': row.isOverdue }">
              {{ formatDueTime(row.dueTime) }}
            </span>
            <span v-if="row.isOverdue" class="overdue-badge">{{ getOverdueText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'PENDING'" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="row.status === 'DONE'" type="success" size="small">已处理</el-tag>
            <el-tag v-else size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.route && row.status === 'PENDING'" text type="primary" @click="handleGo(row)">
              去处理
            </el-button>
            <el-button
              v-if="row.status === 'PENDING' && row.type !== 'APPROVAL' && row.type !== 'REVIEW'"
              text
              type="default"
              @click="handleClose(row)"
            >
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-row">
        <el-pagination
          v-model:current-page="pageNo"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.todos-page {
  width: 100%;
}

.tabs-row {
  margin-bottom: 16px;

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

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
