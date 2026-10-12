<script setup lang="ts">
/**
 * 工作台演示页 (FP-P-12)
 * 依据: UI-L06
 * 包含: 统计卡片、图表
 */
import { ref, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatCard from '@/components/list/StatCard.vue'
import Chart from '@/components/display/Chart.vue'
import { useResponsive } from '@/utils/responsive'
// ECharts 配置类型

const { isMobile } = useResponsive()

const todos = [
  { id: 'a1', tab: '审批', title: '审批单甲', allowed: true },
  { id: 'a2', tab: '审批', title: '审批单乙', allowed: true },
  { id: 'w1', tab: '预警', title: '库存预警', allowed: false },
]
const todoTab = ref('审批')
const todoTip = ref('')
const period = ref('本月')
const updatedAt = ref('2026-10-12 10:00')

function changePeriod(value: string) {
  updatedAt.value = value === '上月' ? '2026-09-30 23:59' : '2026-10-12 10:00'
}
const visibleTodos = computed(() => todos.filter((item) => item.tab === todoTab.value))

function openTodo(item: { allowed: boolean; title: string }) {
  if (!item.allowed) {
    todoTip.value = '暂无权限'
    return
  }
  todoTip.value = ''
  window.location.hash = 'todo'
}

// 统计数据
const stats = ref([
  { title: '今日订单', value: 128, unit: '单', desc: '较昨日', ratio: 12.5, format: 'number' as const },
  { title: '今日销售额', value: 58600, unit: '元', desc: '较昨日', ratio: -5.2, format: 'money' as const },
  { title: '待处理工单', value: 23, unit: '个', desc: '需在今日内处理' },
  { title: '完成率', value: 89.5, unit: '%', desc: '目标 95%', format: 'percent' as const },
])

// 折线图配置
const lineChartOption = ref({
  title: { text: '近 7 日销售趋势', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: ['10/06', '10/07', '10/08', '10/09', '10/10', '10/11', '10/12'],
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'line',
      data: [42000, 38500, 45200, 52300, 48900, 55600, 58600],
      smooth: true,
      areaStyle: { opacity: 0.1 },
    },
  ],
})

// 饼图配置
const pieChartOption = ref({
  title: { text: '订单状态分布', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'item' },
  legend: { bottom: '5%', left: 'center' },
  series: [
    {
      name: '订单状态',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: [
        { value: 45, name: '待审批' },
        { value: 128, name: '已完成' },
        { value: 23, name: '已驳回' },
        { value: 15, name: '已取消' },
      ],
    },
  ],
})

// 柱状图配置
const barChartOption = ref({
  title: { text: '部门业绩排名', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'value' },
  yAxis: {
    type: 'category',
    data: ['研发部', '市场部', '销售部', '运营部', '客服部'],
  },
  series: [
    {
      name: '业绩',
      type: 'bar',
      data: [85000, 72000, 68000, 45000, 32000],
    },
  ],
})
</script>

<template>
  <AppLayout>
    <div class="workbench-demo">
      <PageHeader title="工作台演示" sub-title="FP-P-12 / UI-L06" />
      <div class="period-row">
        <el-select v-model="period" class="period-select" @change="changePeriod">
          <el-option label="本月" value="本月" />
          <el-option label="上月" value="上月" />
        </el-select>
        <span class="update-time">截至 {{ updatedAt }}</span>
      </div>

      <section class="todo-panel">
        <el-badge :value="3" class="msg-unread">未读消息 3</el-badge>
        <el-radio-group v-model="todoTab">
          <el-radio-button value="审批">审批 2</el-radio-button>
          <el-radio-button value="预警">预警 1</el-radio-button>
        </el-radio-group>
        <el-button v-for="item in visibleTodos" :key="item.id" @click="openTodo(item)">{{ item.title }}</el-button>
        <p v-if="todoTip" class="todo-tip">{{ todoTip }}</p>
      </section>

      <!-- 统计卡片 -->
      <StatCard :items="stats" :cols="4" />

      <!-- 图表区 -->
      <div class="charts-row">
        <div class="chart-card">
          <Chart :option="lineChartOption" :height="300" />
        </div>
        <div class="chart-card">
          <Chart :option="pieChartOption" :height="300" />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card full">
          <Chart :option="barChartOption" :height="300" />
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.workbench-demo {
  width: 100%;
}


.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;

  @media (width <= 767px) {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }
}

.chart-card {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 16px;

  &.full {
    grid-column: span 2;

    @media (width <= 767px) {
      grid-column: span 1;
    }
  }
}
</style>
