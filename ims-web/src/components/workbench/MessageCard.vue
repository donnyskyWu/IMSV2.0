<script setup lang="ts">
/**
 * 消息卡片组件 (B3-MS)
 * 依据: 个人工作台-实现理解 §4.3
 *
 * 功能:
 * - 显示消息标题、来源、时间
 * - 未读状态高亮
 */
import { computed } from 'vue'
import type { MessageItem } from '@/api/workbench'

const props = defineProps<{
  message: MessageItem
}>()

defineEmits<{
  click: []
}>()

const isUnread = computed(() => props.message.readStatus === 'UNREAD')

const timeDisplay = computed(() => {
  if (!props.message.createTime) return ''
  const date = new Date(props.message.createTime)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `今天 ${hours}:${minutes}`
  } else if (diffDays === 1) {
    return '昨天'
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else {
    const month = date.getMonth() + 1
    const day = date.getDate()
    return `${month}/${day}`
  }
})
</script>

<template>
  <div
    class="message-card"
    :class="{ unread: isUnread }"
    @click="$emit('click')"
    data-testid="message-card"
  >
    <div class="message-indicator" v-if="isUnread" />
    <div class="message-content">
      <div class="message-title">{{ message.title }}</div>
      <div class="message-body" v-if="message.body">{{ message.body }}</div>
    </div>
    <div class="message-meta">
      <span v-if="message.sourceModule" class="message-source">{{ message.sourceModule }}</span>
      <span class="message-time">{{ timeDisplay }}</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.message-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background-color: var(--bg);
  border-radius: var(--r-xs);
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;

  &:hover {
    background-color: var(--blue-bg);
  }

  &.unread {
    background-color: var(--blue-bg);
  }

  @media (width <= 767px) {
    padding: 10px;
    flex-direction: column;
    gap: 8px;
  }
}

.message-indicator {
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--blue);

  @media (width <= 767px) {
    top: 14px;
    transform: none;
  }
}

.message-content {
  flex: 1;
  min-width: 0;
  padding-left: 8px;
}

.message-title {
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.message-body {
  font-size: 12px;
  color: var(--text2);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;

  @media (width <= 767px) {
    flex-direction: row;
    align-items: center;
    width: 100%;
    justify-content: space-between;
    padding-left: 8px;
  }
}

.message-source {
  font-size: 12px;
  color: var(--text2);
}

.message-time {
  font-size: 12px;
  color: var(--text3);
}
</style>
