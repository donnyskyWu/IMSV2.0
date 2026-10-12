<script setup lang="ts">
/**
 * StatusTag 状态标签
 * 依据: FP-C09-01
 * 圆点 6px + 文字 + 浅底，颜色与中文名只取字典
 */
import { computed, onMounted } from 'vue'
import { useDictStore } from '@/stores/dict'
import type { ColorType } from '@/types'

interface Props {
  dictType: string
  value: string
}

const props = defineProps<Props>()
const dictStore = useDictStore()

// 加载字典
onMounted(() => {
  dictStore.getDict(props.dictType)
})

// 获取标签文本
const label = computed(() => dictStore.label(props.dictType, props.value))

// 获取颜色类型
const colorType = computed<ColorType>(() => {
  const color = dictStore.color(props.dictType, props.value)
  return color || 'neutral'
})

// 状态色 CSS 变量
const textColor = computed(() => `var(--status-${colorType.value}-text)`)
const bgColor = computed(() => `var(--status-${colorType.value}-bg)`)
</script>

<template>
  <span class="status-tag" :style="{ '--tag-text': textColor, '--tag-bg': bgColor }">
    <span class="status-dot" />
    <span class="status-label">{{ label }}</span>
  </span>
</template>

<style lang="scss" scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background-color: var(--tag-bg);
  border-radius: var(--r-xs);
  font-size: 12px;
  font-weight: 500;
  color: var(--tag-text);
  white-space: nowrap;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--tag-text);
  flex-shrink: 0;
}

.status-label {
  line-height: 1.4;
}
</style>
