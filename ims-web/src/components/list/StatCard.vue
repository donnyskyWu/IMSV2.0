<script setup lang="ts">
/**
 * StatCard / KPI 栅格
 * 依据: FP-C10-01, 00-工作包 §2.1 Q16
 * 桌面: cols 参数 (默认 4)
 * 手机 (Q16): 每行 2 列
 */
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'
import { fmtMoney, fmtPercent, isEmpty } from '@/utils/format'
import type { StatItem } from '@/types'

interface Props {
  items: StatItem[]
  cols?: 4 | 3
}

const props = withDefaults(defineProps<Props>(), {
  cols: 4,
})

const { isMobile } = useResponsive()

// 计算列数 (Q16)
const actualCols = computed(() => (isMobile.value ? 2 : props.cols))

// 格式化值
function formatValue(item: StatItem): string {
  if (isEmpty(item.value)) return '—'

  const val = item.value
  switch (item.format) {
    case 'money':
      return fmtMoney(val)
    case 'percent':
      return fmtPercent(typeof val === 'number' ? val : parseFloat(String(val)))
    default:
      return typeof val === 'number' ? val.toLocaleString() : String(val)
  }
}

// 环比颜色
function getRatioClass(ratio: number | undefined): string {
  if (ratio === undefined || ratio === 0) return 'ratio--neutral'
  return ratio > 0 ? 'ratio--up' : 'ratio--down'
}
</script>

<template>
  <div class="stat-grid" :style="{ '--cols': actualCols }">
    <div
      v-for="(item, index) in items"
      :key="index"
      class="stat-card"
      :class="{ clickable: !!item.onClick }"
      @click="item.onClick?.()"
    >
      <div class="stat-title">{{ item.title }}</div>
      <div class="stat-value">
        {{ formatValue(item) }}
        <span v-if="item.unit" class="stat-unit">{{ item.unit }}</span>
      </div>
      <div v-if="item.desc || item.ratio !== undefined" class="stat-footer">
        <span v-if="item.desc" class="stat-desc">{{ item.desc }}</span>
        <span v-if="item.ratio !== undefined" class="stat-ratio" :class="getRatioClass(item.ratio)">
          <el-icon v-if="item.ratio > 0"><ArrowUp /></el-icon>
          <el-icon v-else-if="item.ratio < 0"><ArrowDown /></el-icon>
          {{ Math.abs(item.ratio) }}%
        </span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(var(--cols), 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background-color: var(--card);
  border-radius: var(--r);
  padding: 18px 20px;
  box-shadow: var(--sh);
  transition: box-shadow 0.2s;

  &.clickable {
    cursor: pointer;

    &:hover {
      box-shadow: var(--sh-h);
    }
  }
}

.stat-title {
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 8px;

  @include mobile {
    // Q12: 手机下最小字号 12px
    font-size: 12px;
  }
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
}

.stat-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--text2);
  margin-left: 4px;
}

.stat-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.stat-desc {
  font-size: 12px;
  color: var(--text2);

  @include mobile {
    font-size: 12px;
  }
}

.stat-ratio {
  display: inline-flex;
  align-items: center;
  font-size: 12px;

  @include mobile {
    font-size: 12px;
  }

  &--up {
    color: var(--green);
  }

  &--down {
    color: var(--red);
  }

  &--neutral {
    color: var(--gray);
  }

  .el-icon {
    margin-right: 2px;
  }
}
</style>
