<script setup lang="ts">
/**
 * Tab 列表演示页 (FP-P-05)
 * 依据: UI-L02 统计卡 + Tab 列表
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Tabs from '@/components/layout/Tabs.vue'
import StatCard from '@/components/list/StatCard.vue'

// Tab 配置
const activeTab = ref('all')
const tabItems = [
  { key: 'all', label: '全部', count: 35 },
  { key: 'pending', label: '待处理', count: 12 },
  { key: 'approved', label: '已通过', count: 18 },
  { key: 'rejected', label: '已驳回', count: 5 },
]

// 统计卡数据
const statItems = [
  { title: '总订单数', value: 35, unit: '个', ratio: 12.5 },
  { title: '待处理', value: 12, unit: '个', ratio: -5.2 },
  { title: '总金额', value: 125680.5, format: 'money' as const, ratio: 8.3 },
  { title: '完成率', value: 68.5, format: 'percent' as const, ratio: 0 },
]
</script>

<template>
  <AppLayout>
    <div class="tabs-list-demo">
      <PageHeader title="Tab 列表演示" sub-title="FP-P-05 / UI-L02" />

      <!-- 统计卡 (4列) -->
      <StatCard :items="statItems" :cols="4" class="stat-section" />

      <!-- Tab 切换 -->
      <Tabs
        v-model:active="activeTab"
        :items="tabItems"
        type="line"
        sync-query="tab"
        class="tabs-section"
      />

      <!-- 列表区域占位 -->
      <div class="list-placeholder">
        <p>当前 Tab: {{ activeTab }}</p>
        <p>这里是 {{ tabItems.find(t => t.key === activeTab)?.label }} 的列表内容</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.tabs-list-demo {
  max-width: 1200px;
}

.stat-section {
  margin-bottom: 20px;
}

.tabs-section {
  margin-bottom: 16px;
}

.list-placeholder {
  padding: 40px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;
  color: var(--text2);
}
</style>
