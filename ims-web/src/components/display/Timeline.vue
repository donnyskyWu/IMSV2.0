<script setup lang="ts">
/**
 * Timeline 时间轴
 * 依据: FP-C-35
 * 用于操作日志、流程记录等
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'
import { fmtTime } from '@/utils/format'

interface TimelineItem {
  time: string
  title: string
  content?: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  icon?: string
}

interface Props {
  items: TimelineItem[]
  reverse?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  reverse: false,
})

const { isMobile } = useResponsive()

// 排序后的列表
const sortedItems = computed(() => {
  if (props.reverse) {
    return [...props.items].reverse()
  }
  return props.items
})

// 获取颜色
function getColor(type?: string): string {
  const colors: Record<string, string> = {
    primary: 'var(--blue)',
    success: 'var(--green)',
    warning: 'var(--orange)',
    danger: 'var(--red)',
    info: 'var(--text2)',
  }
  return colors[type || 'primary'] || colors.primary
}
</script>

<template>
  <div class="timeline" :class="{ 'timeline--mobile': isMobile }">
    <div
      v-for="(item, index) in sortedItems"
      :key="index"
      class="timeline-item"
    >
      <div class="timeline-dot" :style="{ backgroundColor: getColor(item.type) }" />
      <div v-if="index < sortedItems.length - 1" class="timeline-line" />
      <div class="timeline-content">
        <div class="timeline-header">
          <span class="timeline-title">{{ item.title }}</span>
          <span class="timeline-time">{{ fmtTime(item.time) }}</span>
        </div>
        <div v-if="item.content" class="timeline-body">
          {{ item.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.timeline {
  position: relative;
  padding-left: 24px;
}

.timeline-item {
  position: relative;
  padding-bottom: 24px;

  &:last-child {
    padding-bottom: 0;
  }
}

.timeline-dot {
  position: absolute;
  left: -24px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--blue);
}

.timeline-line {
  position: absolute;
  left: -20px;
  top: 20px;
  bottom: -4px;
  width: 2px;
  background-color: var(--line);
}

.timeline-content {
  padding-left: 8px;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.timeline-time {
  font-size: 12px;
  color: var(--text2);
  white-space: nowrap;
}

.timeline-body {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text2);
  line-height: 1.5;
}

// 移动端
.timeline--mobile {
  padding-left: 20px;

  .timeline-dot {
    left: -20px;
    width: 8px;
    height: 8px;
    top: 7px;
  }

  .timeline-line {
    left: -17px;
  }

  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .timeline-time {
    order: -1;
  }
}
</style>
