<script setup lang="ts">
/**
 * UI-L07: 空白页模板
 * 最小布局，只有页头
 */
import { useResponsive } from '@/utils/responsive'

const { isMobile } = useResponsive()
</script>

<template>
  <div class="blank-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header v-if="$slots.header" class="layout-header">
      <slot name="header" />
    </header>

    <!-- 内容 -->
    <main class="layout-content">
      <slot />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.blank-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-header {
  flex-shrink: 0;
}

.layout-content {
  flex: 1;
  min-height: 0;
}

// 移动端
.mobile {
  gap: 12px;
}
</style>
