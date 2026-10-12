<script setup lang="ts">
/**
 * UI-L05: 向导页模板
 * 包含: 步骤条 + 步骤内容 + 底部操作
 */
import { useResponsive } from '@/utils/responsive'

const { isMobile } = useResponsive()
</script>

<template>
  <div class="wizard-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header v-if="$slots.header" class="layout-header">
      <slot name="header" />
    </header>

    <!-- 步骤条 -->
    <nav class="layout-steps">
      <slot name="steps" />
    </nav>

    <!-- 步骤内容 -->
    <main class="layout-content">
      <slot />
    </main>

    <!-- 底部操作 -->
    <footer class="layout-footer">
      <slot name="footer" />
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.wizard-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-header {
  flex-shrink: 0;
}

.layout-steps {
  flex-shrink: 0;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 24px;
}

.layout-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 24px;
}

.layout-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
}

// 移动端
.mobile {
  gap: 12px;

  .layout-steps,
  .layout-content {
    padding: 16px;
  }

  .layout-footer {
    padding: 12px 16px;
  }
}
</style>
