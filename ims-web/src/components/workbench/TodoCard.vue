<script setup lang="ts">
/**
 * 待办卡片组件 (B3-TD)
 * 依据: 个人工作台-实现理解 §4.2
 *
 * 功能:
 * - 显示待办标题、类型、截止时间
 * - 逾期红底高亮 (TD-02)
 */
import { computed } from 'vue'
import type { TodoItem } from '@/api/workbench'

const props = defineProps<{
  todo: TodoItem
}>()

defineEmits<{
  click: []
}>()

const typeLabels: Record<string, { text: string; type: 'primary' | 'warning' | 'info' | 'success' | 'danger' | '' }> = {
  APPROVAL: { text: '审批', type: 'primary' },
  RETURN: { text: '归还', type: 'warning' },
  REVIEW: { text: '审核', type: 'info' },
  CONFIRM: { text: '确认', type: 'success' },
  WARNING: { text: '预警', type: 'warning' },
  ALERT: { text: '告警', type: 'danger' },
  STUDY: { text: '学习', type: '' },
}

const typeInfo = computed(() => {
  return typeLabels[props.todo.type || ''] || { text: props.todo.type || '待办', type: '' }
})

const dueTimeDisplay = computed(() => {
  if (!props.todo.dueTime) return null
  const date = new Date(props.todo.dueTime)
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${month}/${day} ${hours}:${minutes}`
})

const overdueText = computed(() => {
  if (!props.todo.isOverdue) return null
  const days = props.todo.overdueDays || 0
  if (days === 0) return '已逾期'
  return `逾期 ${days} 天`
})
</script>

<template>
  <div
    class="todo-card"
    :class="{ overdue: todo.isOverdue }"
    @click="$emit('click')"
    data-testid="todo-card"
  >
    <div class="todo-content">
      <el-tag :type="typeInfo.type" size="small" class="todo-type">
        {{ typeInfo.text }}
      </el-tag>
      <span class="todo-title">{{ todo.title }}</span>
    </div>
    <div class="todo-meta">
      <span v-if="overdueText" class="overdue-text">{{ overdueText }}</span>
      <span v-else-if="dueTimeDisplay" class="due-time">截止 {{ dueTimeDisplay }}</span>
      <el-icon class="arrow-icon"><arrow-right /></el-icon>
    </div>
  </div>
</template>

<script lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'
export default {
  components: { ArrowRight },
}
</script>

<style lang="scss" scoped>
.todo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background-color: var(--bg);
  border-radius: var(--r-xs);
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--blue-bg);
  }

  &.overdue {
    background-color: var(--danger-bg, #fef0f0);

    &:hover {
      background-color: var(--danger-bg-hover, #fde2e2);
    }
  }

  @media (width <= 767px) {
    padding: 10px;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

.todo-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.todo-type {
  flex-shrink: 0;
}

.todo-title {
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todo-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;

  @media (width <= 767px) {
    width: 100%;
    justify-content: space-between;
  }
}

.due-time {
  font-size: 12px;
  color: var(--text2);
}

.overdue-text {
  font-size: 12px;
  color: var(--danger);
  font-weight: 500;
}

.arrow-icon {
  color: var(--text2);
  font-size: 14px;
}
</style>
