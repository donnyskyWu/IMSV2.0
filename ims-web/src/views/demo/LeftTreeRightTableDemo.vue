<script setup lang="ts">
/**
 * 左树右表演示页 (FP-P-11)
 * 依据: UI-L03 左树右表（部门 → 人员）
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
</script>

<template>
  <AppLayout>
    <div class="left-tree-demo">
      <PageHeader title="左树右表" sub-title="FP-P-11 / UI-L03" />
      <div class="placeholder">
        <p>左树右表布局演示区域</p>
        <p>左侧: UI-C42 部门树</p>
        <p>右侧: 人员列表（姓名、用户名、主部门、所属部门、状态）</p>
        <p>右表操作: 新建人员、调整部门、删除</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.left-tree-demo {
  width: 100%;
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
