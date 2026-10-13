<script setup lang="ts">
/**
 * 个人工作台首页 (B3-WB)
 * 依据: 个人工作台-实现理解 §4.1
 *
 * 功能:
 * - 问候区与摘要 (WB-02)
 * - 数据卡片 (WB-03): 只出待办数、未读消息数
 * - 待办预览卡 (WB-04)
 * - 消息预览卡 (WB-05)
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/layout/PageHeader.vue'
import TodoCard from '@/components/workbench/TodoCard.vue'
import MessageCard from '@/components/workbench/MessageCard.vue'
import { workbenchApi, todoApi, messageApi, type DashboardData, type TodoItem, type MessageItem } from '@/api/workbench'
import { useAuthStore } from '@/stores/auth'
import { useTodoActions } from '@/composables/useTodoActions'
import { useResponsive } from '@/utils/responsive'
import { greetingForHour } from '@/utils/greeting'
import { TODO_TABS } from '@/utils/todo-display'

const router = useRouter()
const authStore = useAuthStore()
useResponsive()

const loading = ref(true)
const dashboard = ref<DashboardData | null>(null)
const todos = ref<TodoItem[]>([])
const messages = ref<MessageItem[]>([])
const currentTab = ref('all')

const greeting = computed(() => greetingForHour(new Date().getHours()))

const nickname = computed(() => authStore.user?.nickname || '用户')

const profileLine = computed(() => {
  const user = authStore.user
  if (!user) return ''
  const parts: string[] = []
  const dept = user.mainDeptName || user.deptName
  if (dept) parts.push(`主部门：${dept}`)
  if (user.roleNames?.length) parts.push(`角色：${user.roleNames.join('、')}`)
  return parts.join(' · ')
})

function todoQuery() {
  return {
    type: currentTab.value === 'all' ? undefined : currentTab.value,
    status: 'PENDING',
    pageSize: 10,
  }
}

async function loadTodos() {
  const todosRes = await todoApi.getMyPage(todoQuery())
  if (todosRes.code === 0 && todosRes.data) {
    todos.value = todosRes.data.list
  }
}

async function fetchData() {
  loading.value = true
  try {
    const [dashboardRes, todosRes, messagesRes] = await Promise.all([
      workbenchApi.getDashboard(),
      todoApi.getMyPage(todoQuery()),
      messageApi.getMyPage({ pageSize: 10 }),
    ])

    if (dashboardRes.code === 0 && dashboardRes.data) {
      dashboard.value = dashboardRes.data
    }
    if (todosRes.code === 0 && todosRes.data) {
      todos.value = todosRes.data.list
    }
    if (messagesRes.code === 0 && messagesRes.data) {
      messages.value = messagesRes.data.list
    }
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

function goToTodos() {
  router.push({ path: '/ims/workbench/todos', query: { tab: currentTab.value } })
}

function goToMessages() {
  router.push('/ims/workbench/messages')
}

function handleTabChange() {
  loadTodos()
}

const { handleGo, handleClose } = useTodoActions(fetchData)

function handleMessageClick(message: MessageItem) {
  if (message.route) {
    router.push(message.route)
  } else {
    router.push('/ims/workbench/messages')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="workbench-page">
      <PageHeader :title="`${greeting}，${nickname}`" :sub-title="profileLine" />

      <!-- 数据卡片区 -->
      <div class="stats-cards">
        <div class="stat-card" @click="goToTodos" data-testid="stat-todo">
          <div class="stat-value">{{ dashboard?.todoCount || 0 }}</div>
          <div class="stat-label">待办事项</div>
          <div v-if="dashboard?.todoOverdue" class="stat-extra danger">
            {{ dashboard.todoOverdue }} 项已过期
          </div>
        </div>
        <div class="stat-card" @click="goToMessages" data-testid="stat-message">
          <div class="stat-value">{{ dashboard?.unreadMessageCount || 0 }}</div>
          <div class="stat-label">未读消息</div>
        </div>
      </div>

      <!-- 待办预览卡 -->
      <section class="preview-section" data-testid="todo-preview">
        <div class="section-header">
          <h3>待办中心</h3>
          <el-button text type="primary" @click="goToTodos">查看更多</el-button>
        </div>
        <div class="todo-tabs">
          <el-radio-group v-model="currentTab" size="small" @change="handleTabChange">
            <el-radio-button v-for="tab in TODO_TABS" :key="tab.key" :value="tab.key">
              {{ tab.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <div v-if="loading" class="preview-loading">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else-if="todos.length === 0" class="preview-empty">
          暂无待办
        </div>
        <div v-else class="preview-list">
          <TodoCard
            v-for="item in todos"
            :key="item.id"
            :todo="item"
            @go="handleGo(item)"
            @close="handleClose(item)"
          />
        </div>
      </section>

      <!-- 消息预览卡 -->
      <section class="preview-section" data-testid="message-preview">
        <div class="section-header">
          <h3>消息通知</h3>
          <el-button text type="primary" @click="goToMessages">查看更多</el-button>
        </div>
        <div v-if="loading" class="preview-loading">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else-if="messages.length === 0" class="preview-empty">
          暂无消息
        </div>
        <div v-else class="preview-list">
          <MessageCard
            v-for="item in messages"
            :key="item.id"
            :message="item"
            @click="handleMessageClick(item)"
          />
        </div>
      </section>
  </div>
</template>

<style lang="scss" scoped>
.workbench-page {
  width: 100%;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  @media (width <= 767px) {
    gap: 12px;
    margin-bottom: 16px;
  }
}

.stat-card {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 20px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    border-color: var(--blue);
    box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
  }

  @media (width <= 767px) {
    padding: 16px;
  }
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--blue);
  line-height: 1.2;

  @media (width <= 767px) {
    font-size: 28px;
  }
}

.stat-label {
  font-size: 14px;
  color: var(--text2);
  margin-top: 4px;
}

.stat-extra {
  font-size: 12px;
  margin-top: 8px;

  &.danger {
    color: var(--danger);
  }
}

.preview-section {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 16px;
  margin-bottom: 16px;

  @media (width <= 767px) {
    padding: 12px;
    margin-bottom: 12px;
  }
}

.todo-tabs {
  margin-bottom: 12px;
  max-width: 100%;
  overflow-x: auto;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 8px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin: 0;
  }
}

.preview-loading {
  padding: 16px 0;
}

.preview-empty {
  padding: 32px 0;
  text-align: center;
  color: var(--text2);
  font-size: 14px;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
