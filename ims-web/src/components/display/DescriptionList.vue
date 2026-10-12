<script setup lang="ts">
/**
 * DescriptionList 描述列表
 * 依据: FP-C-36
 * 用于详情页的字段展示
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'
import StatusTag from '@/components/list/StatusTag.vue'
import MaskedText from './MaskedText.vue'
import MoneyText from './MoneyText.vue'

interface DescItem {
  label: string
  value?: string | number | null
  type?: 'text' | 'status' | 'masked' | 'money' | 'link'
  dictType?: string
  span?: number
  link?: string
}

interface Props {
  items: DescItem[]
  columns?: number
  labelWidth?: number | string
  border?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  columns: 2,
  labelWidth: 100,
  border: false,
})

const { isMobile } = useResponsive()

// 移动端单列
const actualColumns = computed(() => {
  return isMobile.value ? 1 : props.columns
})

// 标签宽度样式
const labelStyle = computed(() => {
  if (typeof props.labelWidth === 'number') {
    return { width: `${props.labelWidth}px` }
  }
  return { width: props.labelWidth }
})

// 空值占位
function emptyValue(val?: string | number | null): string {
  if (val === null || val === undefined || val === '') {
    return '-'
  }
  return String(val)
}
</script>

<template>
  <div
    class="description-list"
    :class="{
      'description-list--border': border,
      'description-list--mobile': isMobile,
    }"
    :style="{ '--columns': actualColumns }"
  >
    <div
      v-for="(item, index) in items"
      :key="index"
      class="desc-item"
      :style="{ '--span': item.span || 1 }"
    >
      <div class="desc-label" :style="labelStyle">
        {{ item.label }}
      </div>
      <div class="desc-value">
        <!-- 状态标签 -->
        <StatusTag
          v-if="item.type === 'status' && item.dictType"
          :dict-type="item.dictType"
          :value="String(item.value)"
        />

        <!-- 脱敏文本 -->
        <MaskedText
          v-else-if="item.type === 'masked'"
          :value="String(item.value || '')"
        />

        <!-- 金额 -->
        <MoneyText
          v-else-if="item.type === 'money'"
          :value="Number(item.value) || 0"
        />

        <!-- 链接 -->
        <a
          v-else-if="item.type === 'link' && item.link"
          :href="item.link"
          target="_blank"
          class="desc-link"
        >
          {{ emptyValue(item.value) }}
        </a>

        <!-- 普通文本 -->
        <span v-else>{{ emptyValue(item.value) }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.description-list {
  display: grid;
  grid-template-columns: repeat(var(--columns), 1fr);
  gap: 16px;
}

.desc-item {
  display: flex;
  grid-column: span var(--span);
}

.desc-label {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--text2);
  padding-right: 12px;

  &::after {
    content: ':';
  }
}

.desc-value {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: var(--text);
  word-break: break-all;
}

.desc-link {
  color: var(--blue);
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

// 边框样式
.description-list--border {
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 16px;

  .desc-item {
    padding: 12px 0;
    border-bottom: 1px solid var(--line);

    &:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    &:first-child {
      padding-top: 0;
    }
  }
}

// 移动端
.description-list--mobile {
  gap: 12px;

  .desc-item {
    flex-direction: column;
    gap: 4px;
  }

  .desc-label {
    padding-right: 0;
  }
}
</style>
