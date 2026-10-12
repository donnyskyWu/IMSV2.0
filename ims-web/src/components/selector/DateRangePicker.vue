<script setup lang="ts">
/**
 * DateRangePicker 日期范围选择器
 * 依据: FP-C15-06
 * 带快捷选项
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'
import dayjs from 'dayjs'

interface Props {
  modelValue?: [string, string] | null
  placeholder?: [string, string]
  disabled?: boolean
  clearable?: boolean
  showShortcuts?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: () => ['开始日期', '结束日期'],
  disabled: false,
  clearable: true,
  showShortcuts: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: [string, string] | null): void
  (e: 'change', val: [string, string] | null): void
}>()

const { isMobile } = useResponsive()

// 快捷选项
const shortcuts = computed(() => {
  if (!props.showShortcuts) return []
  
  return [
    {
      text: '今天',
      value: () => {
        const today = dayjs().format('YYYY-MM-DD')
        return [today, today]
      },
    },
    {
      text: '最近7天',
      value: () => {
        const end = dayjs().format('YYYY-MM-DD')
        const start = dayjs().subtract(6, 'day').format('YYYY-MM-DD')
        return [start, end]
      },
    },
    {
      text: '最近30天',
      value: () => {
        const end = dayjs().format('YYYY-MM-DD')
        const start = dayjs().subtract(29, 'day').format('YYYY-MM-DD')
        return [start, end]
      },
    },
    {
      text: '本月',
      value: () => {
        const start = dayjs().startOf('month').format('YYYY-MM-DD')
        const end = dayjs().endOf('month').format('YYYY-MM-DD')
        return [start, end]
      },
    },
    {
      text: '上月',
      value: () => {
        const lastMonth = dayjs().subtract(1, 'month')
        const start = lastMonth.startOf('month').format('YYYY-MM-DD')
        const end = lastMonth.endOf('month').format('YYYY-MM-DD')
        return [start, end]
      },
    },
    {
      text: '本季度',
      value: () => {
        const start = dayjs().startOf('quarter').format('YYYY-MM-DD')
        const end = dayjs().endOf('quarter').format('YYYY-MM-DD')
        return [start, end]
      },
    },
    {
      text: '本年',
      value: () => {
        const start = dayjs().startOf('year').format('YYYY-MM-DD')
        const end = dayjs().endOf('year').format('YYYY-MM-DD')
        return [start, end]
      },
    },
  ]
})

function handleChange(val: [string, string] | null) {
  emit('update:modelValue', val)
  emit('change', val)
}
</script>

<template>
  <el-date-picker
    :model-value="modelValue"
    type="daterange"
    range-separator="~"
    :start-placeholder="placeholder[0]"
    :end-placeholder="placeholder[1]"
    :disabled="disabled"
    :clearable="clearable"
    :shortcuts="shortcuts"
    value-format="YYYY-MM-DD"
    class="date-range-picker"
    :class="{ 'date-range-picker--mobile': isMobile }"
    @update:model-value="handleChange"
  />
</template>

<style lang="scss" scoped>
.date-range-picker {
  width: 100%;
}

// 移动端
.date-range-picker--mobile {
  :deep(.el-input__wrapper) {
    min-height: var(--min-touch-size);
  }
}
</style>
