<script setup lang="ts">
/**
 * 展示组件演示页 (FP-P-09)
 */
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatCard from '@/components/list/StatCard.vue'

// 统计卡数据 (cols=3)
const statItems = [
  { title: '总金额', value: 125680.5, format: 'money' as const, ratio: 8.3 },
  { title: '完成率', value: 68.5, format: 'percent' as const, ratio: -2.1 },
  { title: '订单数', value: 35, ratio: 0 },
]
</script>

<template>
  <AppLayout>
    <div class="display-demo">
      <PageHeader title="展示组件" sub-title="FP-P-09" />

      <!-- 统计卡 (3列) -->
      <section class="demo-section">
        <h3>StatCard (3列)</h3>
        <StatCard :items="statItems" :cols="3" />
      </section>

      <div class="placeholder">
        <p>展示组件演示区域</p>
        <p>包含: Timeline、DescriptionList、MaskedText / MoneyText / PercentText、Chart、TraceGraph</p>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.display-demo {
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

.placeholder {
  padding: 60px 20px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  text-align: center;
  color: var(--text2);
}
</style>
