<script setup lang="ts">
/**
 * UI-L08: 标签列表页模板
 * 包含: PageHeader + Tabs + QueryBar + DataTable + Pagination
 */
import { useResponsive } from '@/utils/responsive'

const { isMobile } = useResponsive()
</script>

<template>
  <div class="tabs-list-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header class="layout-header">
      <slot name="header" />
    </header>

    <!-- 标签页 -->
    <nav class="layout-tabs">
      <slot name="tabs" />
    </nav>

    <!-- 查询区 -->
    <section v-if="$slots.query" class="layout-query">
      <slot name="query" />
    </section>

    <!-- 表格区 -->
    <section class="layout-table">
      <slot name="table" />
    </section>

    <!-- 分页区 -->
    <footer v-if="$slots.pagination" class="layout-pagination">
      <slot name="pagination" />
    </footer>

    <!-- 其他插槽 -->
    <slot />
  </div>
</template>

<style lang="scss" scoped>
.tabs-list-layout {
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

.layout-query {
  flex-shrink: 0;
}

.layout-table {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.layout-pagination {
  flex-shrink: 0;
}

// 移动端
.mobile {
  gap: 12px;

  .layout-tabs {
    padding: 0 12px;
  }
}
</style>
