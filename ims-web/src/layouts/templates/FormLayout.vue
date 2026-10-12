<script setup lang="ts">
/**
 * UI-L04: 表单页模板
 * 包含: PageHeader + 表单区 + 底部操作
 */
import { useResponsive } from '@/utils/responsive'

interface Props {
  maxWidth?: number
  centered?: boolean
}

withDefaults(defineProps<Props>(), {
  maxWidth: 800,
  centered: true,
})

const { isMobile } = useResponsive()
</script>

<template>
  <div class="form-layout" :class="{ mobile: isMobile }">
    <!-- 页头 -->
    <header class="layout-header">
      <slot name="header" />
    </header>

    <!-- 表单区 -->
    <main
      class="layout-form"
      :class="{ centered }"
      :style="{ '--max-width': `${maxWidth}px` }"
    >
      <div class="form-container">
        <slot />
      </div>
    </main>

    <!-- 底部操作 -->
    <footer class="layout-footer">
      <slot name="footer">
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary">提交</el-button>
      </slot>
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.form-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.layout-header {
  flex-shrink: 0;
}

.layout-form {
  flex: 1;
  min-height: 0;
  overflow-y: auto;

  &.centered {
    display: flex;
    justify-content: center;
  }

  .form-container {
    width: 100%;
    max-width: var(--max-width);
    background-color: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--r-s);
    padding: 24px;
  }
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

  .layout-form {
    .form-container {
      padding: 16px;
    }
  }

  .layout-footer {
    padding: 12px 16px;
  }
}
</style>
