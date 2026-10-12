<script setup lang="ts">
/**
 * UI-L01: 标准列表页模板
 * 包含: PageHeader + QueryBar + DataTable + Pagination
 */
import { useResponsive } from '@/utils/responsive'

const { isMobile } = useResponsive()
</script>

<template>
  <div class="standard-list-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header class="layout-header">
      <slot name="header" />
    </header>

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

    <!-- 其他插槽 (抽屉、弹窗等) -->
    <slot />
  </div>
</template>

<style lang="scss" scoped>
.standard-list-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-header {
  flex-shrink: 0;
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
}
</style>
