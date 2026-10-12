<script setup lang="ts">
/**
 * 选择器演示页 (FP-P-07)
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
</script>

<template>
  <AppLayout>
    <div class="selectors-demo">
      <PageHeader title="选择器演示" sub-title="FP-P-07" />
      <div class="placeholder">
        <p>选择器组件演示区域</p>
        <p>包含: RemoteSelect、UserSelect、DeptTreeSelect、RoleSelect、DictSelect 等</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.selectors-demo {
  max-width: 800px;
}

.placeholder {
  padding: 60px 20px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;
  color: var(--text2);
}
</style>
