<script setup lang="ts">
/**
 * UI-L03: 详情页模板
 * 包含: PageHeader + 详情区块 (可分 Tab)
 */
import { useResponsive } from '@/utils/responsive'

const { isMobile } = useResponsive()
</script>

<template>
  <div class="detail-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header class="layout-header">
      <slot name="header" />
    </header>

    <!-- 标签页 (可选) -->
    <nav v-if="$slots.tabs" class="layout-tabs">
      <slot name="tabs" />
    </nav>

    <!-- 内容区 -->
    <main class="layout-content">
      <slot />
    </main>

    <!-- 底部操作区 (可选) -->
    <footer v-if="$slots.footer" class="layout-footer">
      <slot name="footer" />
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.detail-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-header {
  flex-shrink: 0;
}

.layout-tabs {
  flex-shrink: 0;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 0 16px;

  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }
}

.layout-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.layout-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
}

// 移动端
.mobile {
  gap: 12px;

  .layout-footer {
    padding: 12px;
  }
}
</style>
