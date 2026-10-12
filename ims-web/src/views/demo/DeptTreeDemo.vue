<script setup lang="ts">
/**
 * 部门树演示页 (FP-P-10)
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
</script>

<template>
  <AppLayout>
    <div class="dept-tree-demo">
      <PageHeader title="部门树" sub-title="FP-P-10 / UI-C42" />
      <div class="placeholder">
        <p>部门树组件演示区域</p>
        <p>右侧显示事件日志（select 参数）、当前权限码切换说明</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.dept-tree-demo {
  max-width: 1000px;
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
