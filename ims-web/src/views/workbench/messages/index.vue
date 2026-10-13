<script setup lang="ts">
/**
 * 消息中心 (B3-MS)
 * 依据: 个人工作台-实现理解 §4.3
 *
 * 功能:
 * - MS-01: 列表与筛选
 * - MS-02: 消息详情与标记已读
 * - MS-03: 全部已读
 * - MS-04: 未读数
 * - MS-05: 查看来源
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { messageApi, type MessageItem } from '@/api/workbench'
import { useAuthStore } from '@/stores/auth'
import { useUnreadStore } from '@/stores/unread'
import { isRouteAccessible } from '@/utils/route-accessible'
import { isRegisteredMenuless } from '@/utils/menuless-route'
import { ApiError } from '@/api/request'

const router = useRouter()
const authStore = useAuthStore()
const unreadStore = useUnreadStore()

const loading = ref(false)
const messages = ref<MessageItem[]>([])
const total = ref(0)

const currentTab = ref<'all' | 'UNREAD' | 'READ'>('all')
const keyword = ref('')
const pageNo = ref(1)
const pageSize = ref(20)

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'UNREAD', label: '未读' },
  { key: 'READ', label: '已读' },
]

function formatTime(timeStr: string | null): string {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

async function fetchData() {
  loading.value = true
  try {
    const res = await messageApi.getMyPage({
      readStatus: currentTab.value === 'all' ? undefined : currentTab.value,
      keyword: keyword.value || undefined,
      pageNo: pageNo.value,
      pageSize: pageSize.value,
    })

    if (res.code === 0 && res.data) {
      messages.value = res.data.list
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

function handleTabChange(key: 'all' | 'UNREAD' | 'READ') {
  currentTab.value = key
  pageNo.value = 1
  fetchData()
}

function handleSearch() {
  pageNo.value = 1
  fetchData()
}

function handleReset() {
  keyword.value = ''
  pageNo.value = 1
  fetchData()
}

function handlePageChange(page: number) {
  pageNo.value = page
  fetchData()
}

async function handleMarkAllRead() {
  try {
    const res = await messageApi.markAllRead()
    if (res.code === 0) {
      unreadStore.reset()
      messages.value.forEach((m) => (m.readStatus = 'READ'))
      ElMessage.success(`已将 ${res.data?.updated || 0} 条消息标为已读`)
      fetchData()
    }
  } catch {
    // 错误已由全局处理
  }
}

async function handleView(message: MessageItem) {
  if (message.readStatus === 'UNREAD') {
    try {
      await messageApi.markRead([message.id])
      unreadStore.decrement()
      message.readStatus = 'READ'
    } catch {
      // 静默失败
    }
  }

  if (message.route) {
    if (!isRouteAccessible(message.route, authStore.menus, isRegisteredMenuless(message.route))) {
      ElMessage.warning('暂无权限访问')
      return
    }

    try {
      await router.push(message.route)
    } catch (err) {
      if (err instanceof ApiError && err.code === 1504) {
        ElMessage.warning('单据已被处理或删除')
      }
    }
  }
}

async function handleMarkRead(message: MessageItem) {
  if (message.readStatus === 'READ') return

  try {
    await messageApi.markRead([message.id])
    unreadStore.decrement()
    message.readStatus = 'READ'
    ElMessage.success('已标为已读')
  } catch {
    // 错误已由全局处理
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <AppLayout>
    <div class="messages-page">
      <PageHeader title="消息中心">
        <template #actions>
          <el-button type="primary" @click="handleMarkAllRead">全部已读</el-button>
        </template>
      </PageHeader>

      <!-- Tab 切换 -->
      <div class="tabs-row">
        <el-radio-group v-model="currentTab" @change="handleTabChange">
          <el-radio-button v-for="tab in tabs" :key="tab.key" :value="tab.key">
            {{ tab.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-row">
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
      <el-table :data="messages" v-loading="loading" style="width: 100%" row-key="id">
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.readStatus === 'UNREAD'" type="primary" size="small">未读</el-tag>
            <el-tag v-else type="info" size="small">已读</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ 'unread-title': row.readStatus === 'UNREAD' }">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="body" label="内容" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sourceModule" label="来源" width="120" show-overflow-tooltip />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.createTime) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.route" text type="primary" @click="handleView(row)">
              查看来源
            </el-button>
            <el-button v-if="row.readStatus === 'UNREAD'" text type="default" @click="handleMarkRead(row)">
              标为已读
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
.messages-page {
  width: 100%;
}

.tabs-row {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.unread-title {
  font-weight: 600;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
