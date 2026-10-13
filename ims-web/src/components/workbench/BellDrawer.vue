<script setup lang="ts">
/**
 * 铃铛抽屉组件 (B3-MS-04)
 * 依据: 个人工作台-实现理解 §7.2
 *
 * 功能:
 * - 420px 右侧抽屉
 * - 展示最近 20 条消息
 * - 点击已读 -1
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MessageCard from './MessageCard.vue'
import { messageApi, type MessageItem } from '@/api/workbench'
import { useUnreadStore } from '@/stores/unread'
import { useAuthStore } from '@/stores/auth'
import { isRouteAccessible } from '@/utils/route-accessible'
import { ApiError } from '@/api/request'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const router = useRouter()
const unreadStore = useUnreadStore()
const authStore = useAuthStore()

const loading = ref(false)
const messages = ref<MessageItem[]>([])

async function fetchMessages() {
  loading.value = true
  try {
    const res = await messageApi.getMyPage({ pageSize: 20 })
    if (res.code === 0 && res.data) {
      messages.value = res.data.list
    }
  } finally {
    loading.value = false
  }
}

async function handleMessageClick(message: MessageItem) {
  emit('update:visible', false)

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
    if (!isRouteAccessible(message.route, authStore.menus)) {
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
  } else {
    router.push('/ims/workbench/messages')
  }
}

function handleMarkAllRead() {
  messageApi.markAllRead().then((res) => {
    if (res.code === 0) {
      unreadStore.reset()
      messages.value.forEach((m) => (m.readStatus = 'READ'))
      ElMessage.success(`已将 ${res.data?.updated || 0} 条消息标为已读`)
    }
  })
}

function goToMessageCenter() {
  emit('update:visible', false)
  router.push('/ims/workbench/messages')
}

watch(() => props.visible, (val) => {
  if (val) {
    fetchMessages()
  }
})
</script>

<template>
  <el-drawer
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="消息通知"
    direction="rtl"
    :size="420"
    :with-header="true"
    class="bell-drawer"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">消息通知</span>
        <el-button v-if="unreadStore.count > 0" text type="primary" @click="handleMarkAllRead">
          全部已读
        </el-button>
      </div>
    </template>

    <div v-if="loading" class="drawer-loading">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="messages.length === 0" class="drawer-empty">
      暂无消息
    </div>

    <div v-else class="drawer-list">
      <MessageCard
        v-for="item in messages"
        :key="item.id"
        :message="item"
        @click="handleMessageClick(item)"
      />
    </div>

    <template #footer>
      <el-button type="primary" @click="goToMessageCenter" style="width: 100%">
        查看全部消息
      </el-button>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.drawer-loading {
  padding: 16px;
}

.drawer-empty {
  padding: 64px 16px;
  text-align: center;
  color: var(--text2);
  font-size: 14px;
}

.drawer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 4px;
}

:deep(.el-drawer__body) {
  padding: 12px;
}

:deep(.el-drawer__footer) {
  padding: 12px 16px;
}
</style>
