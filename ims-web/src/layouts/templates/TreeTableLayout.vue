<script setup lang="ts">
/**
 * UI-L02: 左树右表页模板
 * 包含: 左侧树 + 右侧标准列表
 */
import { useResponsive } from '@/utils/responsive'

interface Props {
  treeWidth?: number
}

withDefaults(defineProps<Props>(), {
  treeWidth: 280,
})

const { isMobile } = useResponsive()
</script>

<template>
  <div class="tree-table-layout" :class="{ mobile: isMobile }">
    <!-- 桌面端: 左树右表 -->
    <template v-if="!isMobile">
      <aside class="layout-tree" :style="{ width: `${treeWidth}px` }">
        <slot name="tree" />
      </aside>
      <main class="layout-main">
        <slot name="header" />
        <slot name="query" />
        <slot name="table" />
        <slot name="pagination" />
        <slot />
      </main>
    </template>

    <!-- 移动端: 树收进抽屉 -->
    <template v-else>
      <slot name="mobile-tree-bar" />
      <main class="layout-main">
        <slot name="header" />
        <slot name="query" />
        <slot name="table" />
        <slot name="pagination" />
        <slot />
      </main>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.tree-table-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.layout-tree {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.layout-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// 移动端
.mobile {
  flex-direction: column;
  gap: 12px;
}
</style>
