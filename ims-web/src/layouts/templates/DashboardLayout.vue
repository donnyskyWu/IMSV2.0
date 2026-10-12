<script setup lang="ts">
/**
 * UI-L06: 仪表盘页模板
 * 包含: 统计卡片 + 图表区域
 */
import { useResponsive } from '@/utils/responsive'

interface Props {
  columns?: number
}

withDefaults(defineProps<Props>(), {
  columns: 4,
})

const { isMobile } = useResponsive()
</script>

<template>
  <div class="dashboard-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header v-if="$slots.header" class="layout-header">
      <slot name="header" />
    </header>

    <!-- 统计卡片区 -->
    <section
      v-if="$slots.stats"
      class="layout-stats"
      :style="{ '--columns': isMobile ? 2 : columns }"
    >
      <slot name="stats" />
    </section>

    <!-- 图表区 -->
    <section v-if="$slots.charts" class="layout-charts">
      <slot name="charts" />
    </section>

    <!-- 其他内容 -->
    <section v-if="$slots.default" class="layout-content">
      <slot />
    </section>
  </div>
</template>

<style lang="scss" scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.layout-header {
  flex-shrink: 0;
}

.layout-stats {
  display: grid;
  grid-template-columns: repeat(var(--columns), 1fr);
  gap: 16px;
}

.layout-charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.layout-content {
  flex: 1;
}

// 移动端
.mobile {
  gap: 12px;

  .layout-stats {
    gap: 12px;
  }

  .layout-charts {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
