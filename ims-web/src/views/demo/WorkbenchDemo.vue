<script setup lang="ts">
/**
 * 工作台演示页 (FP-P-12 之一)
 * 依据: UI-L05 工作台页
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Tabs from '@/components/layout/Tabs.vue'
import { ref } from 'vue'

const activeTab = ref('approval')
const tabItems = [
  { key: 'approval', label: '审批', count: 2 },
  { key: 'return', label: '归还', count: 0 },
  { key: 'review', label: '审核', count: 1 },
  { key: 'confirm', label: '确认', count: 0 },
  { key: 'alert', label: '预警', count: 1 },
]
</script>

<template>
  <AppLayout>
    <div class="workbench-demo">
      <PageHeader title="工作台" sub-title="FP-P-12 / UI-L05" :show-scope="true" />

      <!-- 待办 Tab -->
      <section class="demo-section">
        <h3>待办事项</h3>
        <Tabs v-model:active="activeTab" :items="tabItems" type="pill" />
        <div class="todo-list">
          <p>当前 Tab: {{ activeTab }}</p>
          <p>待办列表区域</p>
        </div>
      </section>

      <!-- 消息区域 -->
      <section class="demo-section">
        <h3>消息</h3>
        <div class="placeholder">
          <p>消息列表: 全部 / 未读 / 已读</p>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.workbench-demo {
  max-width: 1000px;
}

.demo-section {
  margin-bottom: 24px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
  }
}

.todo-list,
.placeholder {
  padding: 40px 20px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;
  color: var(--text2);
}
</style>
