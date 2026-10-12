<script setup lang="ts">
/**
 * Chart 图表组件
 * 依据: FP-C-38
 * 基于 ECharts 的图表封装
 */
import { ref, computed, watch, onMounted, onUnmounted, shallowRef } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useDebounceFn } from '@vueuse/core'
import { useResponsive } from '@/utils/responsive'

// 注册 ECharts 组件
echarts.use([
  BarChart,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
])

type EChartsOption = echarts.ComposeOption<
  | import('echarts/charts').BarSeriesOption
  | import('echarts/charts').LineSeriesOption
  | import('echarts/charts').PieSeriesOption
  | import('echarts/components').TitleComponentOption
  | import('echarts/components').TooltipComponentOption
  | import('echarts/components').LegendComponentOption
  | import('echarts/components').GridComponentOption
>

interface Props {
  option: EChartsOption
  height?: string | number
  loading?: boolean
  theme?: 'light' | 'dark'
}

const props = withDefaults(defineProps<Props>(), {
  height: 300,
  loading: false,
  theme: 'light',
})

const chartRef = ref<HTMLDivElement>()
const chartInstance = shallowRef<echarts.ECharts>()
const { isMobile } = useResponsive()

// 高度样式
const heightStyle = computed(() => {
  if (typeof props.height === 'number') {
    return `${props.height}px`
  }
  return props.height
})

// 初始化图表
function initChart() {
  if (!chartRef.value) return

  chartInstance.value = echarts.init(chartRef.value, props.theme)
  chartInstance.value.setOption(props.option)

  if (props.loading) {
    chartInstance.value.showLoading()
  }
}

// 更新图表
function updateChart() {
  if (!chartInstance.value) return

  chartInstance.value.setOption(props.option, true)

  if (props.loading) {
    chartInstance.value.showLoading()
  } else {
    chartInstance.value.hideLoading()
  }
}

// 响应式调整
const handleResize = useDebounceFn(() => {
  chartInstance.value?.resize()
}, 200)

// 监听配置变化
watch(
  () => props.option,
  () => {
    updateChart()
  },
  { deep: true }
)

// 监听加载状态
watch(
  () => props.loading,
  (loading) => {
    if (loading) {
      chartInstance.value?.showLoading()
    } else {
      chartInstance.value?.hideLoading()
    }
  }
)

// 监听主题变化
watch(
  () => props.theme,
  () => {
    chartInstance.value?.dispose()
    initChart()
  }
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance.value?.dispose()
})

// 暴露方法
defineExpose({
  getInstance: () => chartInstance.value,
  resize: () => chartInstance.value?.resize(),
})
</script>

<template>
  <div
    ref="chartRef"
    class="chart"
    :class="{ 'chart--mobile': isMobile }"
    :style="{ height: heightStyle }"
  />
</template>

<style lang="scss" scoped>
.chart {
  width: 100%;
}
</style>
