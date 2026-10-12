<script setup lang="ts">
/**
 * 展示组件演示页 (FP-P-09)
 * 依据: FP-C-35~39
 * 包含: Timeline、DescriptionList、MaskedText、MoneyText、PercentText、Chart、TraceGraph
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Timeline from '@/components/display/Timeline.vue'
import DescriptionList from '@/components/display/DescriptionList.vue'
import MaskedText from '@/components/display/MaskedText.vue'
import MoneyText from '@/components/display/MoneyText.vue'
import PercentText from '@/components/display/PercentText.vue'
import Chart from '@/components/display/Chart.vue'
import TraceGraph from '@/components/display/TraceGraph.vue'
// ECharts 配置类型

// 时间轴数据
const timelineItems = ref([
  { time: '2026-10-12 14:30:00', title: '订单创建', content: '用户提交了订单申请', type: 'primary' as const },
  { time: '2026-10-12 15:00:00', title: '初审通过', content: '财务部门已完成初审', type: 'success' as const },
  { time: '2026-10-12 16:30:00', title: '复审中', content: '等待主管审批', type: 'warning' as const },
  { time: '2026-10-12 17:00:00', title: '审批完成', content: '主管已批准', type: 'success' as const },
])

// 描述列表数据
const descItems = ref([
  { label: '订单编号', value: 'ORD2026100001' },
  { label: '客户名称', value: '张三公司' },
  { label: '订单金额', value: 12800.5, type: 'money' as const },
  { label: '订单状态', value: 'APPROVED', type: 'status' as const, dictType: 'demo_order_status' },
  { label: '联系电话', value: '138****5678', type: 'masked' as const },
  { label: '创建时间', value: '2026-10-12 14:30:00' },
  { label: '备注说明', value: '这是一条较长的备注说明文字，用于展示多行内容的处理效果', span: 2 },
])

// 图表配置
const chartOption = ref({
  title: { text: '月度销售趋势' },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: ['1月', '2月', '3月', '4月', '5月', '6月'],
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'line',
      data: [820, 932, 901, 1234, 1290, 1330],
      smooth: true,
    },
  ],
})

// 流程图数据
const flowNodes = ref([
  { id: 'start', label: '开始', type: 'start' as const, status: 'completed' as const },
  { id: 'task1', label: '提交申请', type: 'task' as const, status: 'completed' as const },
  { id: 'gateway1', label: '审批', type: 'gateway' as const, status: 'completed' as const },
  { id: 'task2', label: '财务审核', type: 'task' as const, status: 'running' as const },
  { id: 'end', label: '结束', type: 'end' as const, status: 'pending' as const },
])

const flowEdges = ref([
  { from: 'start', to: 'task1' },
  { from: 'task1', to: 'gateway1' },
  { from: 'gateway1', to: 'task2' },
  { from: 'task2', to: 'end' },
])
</script>

<template>
  <AppLayout>
    <div class="display-demo">
      <PageHeader title="展示组件演示" sub-title="FP-P-09 / FP-C35~C39" />

      <div class="demo-section">
        <h3 class="section-title">1. 时间轴 (Timeline)</h3>
        <Timeline :items="timelineItems" />
      </div>

      <div class="demo-section">
        <h3 class="section-title">2. 描述列表 (DescriptionList)</h3>
        <DescriptionList :items="descItems" :columns="2" />
      </div>

      <div class="demo-section">
        <h3 class="section-title">3. 文本组件</h3>
        <div class="text-demos">
          <div class="text-item">
            <span class="text-label">脱敏文本:</span>
            <MaskedText value="138****5678" :can-view="true" />
          </div>
          <div class="text-item">
            <span class="text-label">金额 (正):</span>
            <MoneyText :value="12800.5" />
          </div>
          <div class="text-item">
            <span class="text-label">金额 (负):</span>
            <MoneyText :value="-500" />
          </div>
          <div class="text-item">
            <span class="text-label">百分比:</span>
            <PercentText :value="85.5" :show-progress="true" />
          </div>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">4. 图表 (Chart)</h3>
        <Chart :option="chartOption" :height="300" />
      </div>

      <div class="demo-section">
        <h3 class="section-title">5. 流程图 (TraceGraph) - 只读</h3>
        <TraceGraph
          :nodes="flowNodes"
          :edges="flowEdges"
          current-node="task2"
          :height="300"
        />
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.display-demo {
  max-width: 900px;
}

.demo-section {
  margin-bottom: 32px;
  padding: 24px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.text-demos {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.text-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .text-label {
    color: var(--text2);
    font-size: 14px;
  }
}

@media (width <= 767px) {
  .text-demos {
    flex-direction: column;
    gap: 16px;
  }
}
</style>
