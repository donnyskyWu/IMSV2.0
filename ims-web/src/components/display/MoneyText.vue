<script setup lang="ts">
/**
 * MoneyText 金额显示
 * 依据: FP-C19-03
 * - 千分位格式化
 * - 负数红色
 * - 可选货币符号
 */
import { computed } from 'vue'
import { fmtMoney } from '@/utils/format'

interface Props {
  value: number
  currency?: string
  precision?: number
  showSign?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  currency: '¥',
  precision: 2,
  showSign: false,
})

// 格式化后的值
const formattedValue = computed(() => {
  return fmtMoney(props.value, props.precision)
})

// 是否负数
const isNegative = computed(() => props.value < 0)

// 是否正数 (用于显示 + 号)
const isPositive = computed(() => props.value > 0)
</script>

<template>
  <span
    class="money-text"
    :class="{
      'money-text--negative': isNegative,
      'money-text--positive': isPositive && showSign,
    }"
  >
    <span v-if="currency" class="currency">{{ currency }}</span>
    <span v-if="isPositive && showSign" class="sign">+</span>
    <span class="amount">{{ formattedValue }}</span>
  </span>
</template>

<style lang="scss" scoped>
.money-text {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.currency {
  margin-right: 2px;
}

.money-text--negative {
  color: var(--red);
}

.money-text--positive {
  color: var(--green);
}

.amount {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
}
</style>
