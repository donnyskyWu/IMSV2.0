<script setup lang="ts">
/**
 * PercentText 百分比显示
 * 依据: FP-C19-04
 */
import { computed } from 'vue'
import { fmtPercent } from '@/utils/format'

interface Props {
  value: number
  precision?: number
  showProgress?: boolean
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  precision: 2,
  showProgress: false,
})

// 格式化后的值
const formattedValue = computed(() => {
  return fmtPercent(props.value, props.precision)
})

// 进度条颜色
const progressColor = computed(() => {
  if (props.color) return props.color
  if (props.value >= 100) return 'var(--green)'
  if (props.value >= 80) return 'var(--blue)'
  if (props.value >= 50) return 'var(--orange)'
  return 'var(--red)'
})
</script>

<template>
  <span class="percent-text">
    <span v-if="showProgress" class="progress-bar">
      <span
        class="progress-fill"
        :style="{
          width: `${Math.min(value, 100)}%`,
          backgroundColor: progressColor,
        }"
      />
    </span>
    <span class="percent-value">{{ formattedValue }}</span>
  </span>
</template>

<style lang="scss" scoped>
.percent-text {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 60px;
  height: 6px;
  background-color: var(--hover);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.percent-value {
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
}
</style>
