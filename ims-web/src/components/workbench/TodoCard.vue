<script setup lang="ts">
/**
 * 待办卡片（首页预览）
 * 类型 Tab 在首页容器上；行内提供〔去处理〕〔关闭〕。
 */
import { computed } from 'vue'
import type { TodoItem } from '@/api/workbench'
import { canCloseTodo, overdueText, todoTypeInfo } from '@/utils/todo-display'

const props = defineProps<{
  todo: TodoItem
}>()

defineEmits<{
  go: []
  close: []
}>()

const typeInfo = computed(() => todoTypeInfo(props.todo.type))

const dueTimeDisplay = computed(() => {
  if (!props.todo.dueTime) return null
  const date = new Date(props.todo.dueTime)
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${month}/${day} ${hours}:${minutes}`
})

const overdueLabel = computed(() => overdueText(props.todo.isOverdue, props.todo.overdueDays || 0))
const showClose = computed(() => props.todo.status === 'PENDING' && canCloseTodo(props.todo.type))
</script>

<template>
  <div
    class="todo-card"
    :class="{ overdue: todo.isOverdue }"
    data-testid="todo-card"
  >
    <div class="todo-content">
      <el-tag :type="typeInfo.type" size="small" class="todo-type">
        {{ typeInfo.text }}
      </el-tag>
      <span class="todo-title">{{ todo.title }}</span>
    </div>
    <div class="todo-meta">
      <span v-if="overdueLabel" class="overdue-text">{{ overdueLabel }}</span>
      <span v-else-if="dueTimeDisplay" class="due-time">截止 {{ dueTimeDisplay }}</span>
      <el-button
        v-if="todo.status === 'PENDING'"
        size="small"
        type="primary"
        @click="$emit('go')"
      >
        去处理
      </el-button>
      <el-button v-if="showClose" size="small" @click="$emit('close')">
        关闭
      </el-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.todo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background-color: var(--bg);
  border-radius: var(--r-xs);
  gap: 8px;

  &.overdue {
    background-color: var(--danger-bg, #fef0f0);
  }

  @media (width <= 767px) {
    padding: 10px;
    flex-direction: column;
    align-items: flex-start;
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
    flex-wrap: wrap;
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
</style>
