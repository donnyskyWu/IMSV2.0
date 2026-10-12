<script setup lang="ts">
/**
 * EmptyState 空状态
 * 依据: FP-C11-01
 * 三种默认文案: "暂无数据" / "暂无权限查看此内容" / "加载失败，请稍后重试"
 * 任何场景不显示 403 白页
 */
import type { EmptyType } from '@/types'

interface Props {
  type?: EmptyType
  desc?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'empty',
})

const emit = defineEmits<{
  (e: 'retry'): void
}>()

// 默认文案
const defaultMessages: Record<EmptyType, string> = {
  empty: '暂无数据',
  noPermission: '暂无权限查看此内容',
  error: '加载失败，请稍后重试',
}

const message = props.desc || defaultMessages[props.type]
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">
      <svg v-if="type === 'empty'" viewBox="0 0 64 64" width="64" height="64">
        <path
          d="M32 8C18.7 8 8 18.7 8 32s10.7 24 24 24 24-10.7 24-24S45.3 8 32 8zm0 44c-11 0-20-9-20-20s9-20 20-20 20 9 20 20-9 20-20 20z"
          fill="currentColor"
          opacity="0.2"
        />
        <path
          d="M22 28h20v2H22zm0 6h14v2H22z"
          fill="currentColor"
          opacity="0.4"
        />
      </svg>
      <svg v-else-if="type === 'noPermission'" viewBox="0 0 64 64" width="64" height="64">
        <path
          d="M32 8C18.7 8 8 18.7 8 32s10.7 24 24 24 24-10.7 24-24S45.3 8 32 8zm0 44c-11 0-20-9-20-20s9-20 20-20 20 9 20 20-9 20-20 20z"
          fill="currentColor"
          opacity="0.2"
        />
        <path
          d="M32 16c-4.4 0-8 3.6-8 8v4h-2v12h20V28h-2v-4c0-4.4-3.6-8-8-8zm4 12H28v-4c0-2.2 1.8-4 4-4s4 1.8 4 4v4z"
          fill="currentColor"
          opacity="0.4"
        />
      </svg>
      <svg v-else viewBox="0 0 64 64" width="64" height="64">
        <path
          d="M32 8C18.7 8 8 18.7 8 32s10.7 24 24 24 24-10.7 24-24S45.3 8 32 8zm0 44c-11 0-20-9-20-20s9-20 20-20 20 9 20 20-9 20-20 20z"
          fill="currentColor"
          opacity="0.2"
        />
        <path
          d="M30 22h4v14h-4zm0 18h4v4h-4z"
          fill="currentColor"
          opacity="0.4"
        />
      </svg>
    </div>
    <p class="empty-text">{{ message }}</p>
    <div v-if="type === 'error'" class="empty-action">
      <el-button type="primary" @click="emit('retry')">重试</el-button>
    </div>
    <slot name="action" />
  </div>
</template>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 44px 20px;
  text-align: center;
}

.empty-icon {
  color: var(--text2);
  margin-bottom: 16px;
}

.empty-text {
  font-size: 13px;
  color: var(--text2);
  margin: 0 0 16px;
  max-width: 300px;
}

.empty-action {
  margin-top: 8px;
}
</style>
