<script setup lang="ts">
/**
 * TraceGraph / FlowDesigner 流程图 (只读)
 * 依据: FP-C-39
 * 第 1 步仅实现只读显示，编辑功能在第 2 步实现
 */
import { computed, ref } from 'vue'
import { useResponsive } from '@/utils/responsive'

interface FlowNode {
  id: string
  label: string
  type: 'start' | 'end' | 'task' | 'gateway' | 'condition'
  status?: 'pending' | 'running' | 'completed' | 'failed'
  x?: number
  y?: number
}

interface FlowEdge {
  from: string
  to: string
  label?: string
}

interface Props {
  nodes: FlowNode[]
  edges: FlowEdge[]
  currentNode?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 400,
})

const { isMobile } = useResponsive()
const scale = ref(1)

const emit = defineEmits<{
  (e: 'node-click', node: FlowNode): void
}>()

function onWheel(event: { deltaY: number }) {
  scale.value = Math.min(2, Math.max(0.5, Number((scale.value + (event.deltaY < 0 ? 0.1 : -0.1)).toFixed(2))))
}

// 节点颜色
function getNodeColor(node: FlowNode): string {
  if (node.id === props.currentNode) {
    return 'var(--blue)'
  }
  switch (node.status) {
    case 'completed':
      return 'var(--green)'
    case 'running':
      return 'var(--blue)'
    case 'failed':
      return 'var(--red)'
    default:
      return 'var(--text2)'
  }
}

// 节点图标
function getNodeIcon(type: FlowNode['type']): string {
  switch (type) {
    case 'start':
      return '○'
    case 'end':
      return '◉'
    case 'gateway':
      return '◇'
    case 'condition':
      return '▽'
    default:
      return '□'
  }
}

// 计算节点位置 (简单的自动布局)
const layoutNodes = computed(() => {
  const nodeMap = new Map<string, FlowNode>()
  props.nodes.forEach((n) => nodeMap.set(n.id, n))

  // 如果节点有位置，使用原位置
  if (props.nodes.some((n) => n.x !== undefined)) {
    return props.nodes
  }

  // 简单的层级布局
  const levels: string[][] = []
  const visited = new Set<string>()
  const inDegree = new Map<string, number>()

  // 计算入度
  props.nodes.forEach((n) => inDegree.set(n.id, 0))
  props.edges.forEach((e) => {
    inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1)
  })

  // BFS 分层
  let queue = props.nodes.filter((n) => inDegree.get(n.id) === 0).map((n) => n.id)
  while (queue.length > 0) {
    levels.push(queue)
    queue.forEach((id) => visited.add(id))

    const nextQueue: string[] = []
    props.edges
      .filter((e) => queue.includes(e.from))
      .forEach((e) => {
        if (!visited.has(e.to) && !nextQueue.includes(e.to)) {
          nextQueue.push(e.to)
        }
      })
    queue = nextQueue
  }

  // 计算位置
  const nodeWidth = 120
  const nodeHeight = 50
  const levelGap = 100
  const nodeGap = 60

  const result: FlowNode[] = []
  levels.forEach((level, levelIndex) => {
    const totalWidth = level.length * nodeWidth + (level.length - 1) * nodeGap
    const startX = (props.nodes.length * nodeWidth - totalWidth) / 2

    level.forEach((nodeId, nodeIndex) => {
      const node = nodeMap.get(nodeId)
      if (node) {
        result.push({
          ...node,
          x: startX + nodeIndex * (nodeWidth + nodeGap),
          y: levelIndex * (nodeHeight + levelGap),
        })
      }
    })
  })

  return result
})

// SVG 视图框
const viewBox = computed(() => {
  if (layoutNodes.value.length === 0) return '0 0 600 400'

  const padding = 60
  const xs = layoutNodes.value.map((n) => n.x || 0)
  const ys = layoutNodes.value.map((n) => n.y || 0)
  const minX = Math.min(...xs) - padding
  const minY = Math.min(...ys) - padding
  const maxX = Math.max(...xs) + 120 + padding
  const maxY = Math.max(...ys) + 50 + padding

  return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`
})

// 获取节点中心点
function getNodeCenter(nodeId: string): { x: number; y: number } {
  const node = layoutNodes.value.find((n) => n.id === nodeId)
  if (!node) return { x: 0, y: 0 }
  return {
    x: (node.x || 0) + 60,
    y: (node.y || 0) + 25,
  }
}

// 生成连线路径
function getEdgePath(edge: FlowEdge): string {
  const from = getNodeCenter(edge.from)
  const to = getNodeCenter(edge.to)
  
  // 简单的直线连接
  return `M ${from.x} ${from.y + 25} L ${to.x} ${to.y - 25}`
}
</script>

<template>
  <div
    class="trace-graph"
    :class="{ 'trace-graph--mobile': isMobile }"
    :style="{ height: `${height}px` }"
    :data-scale="scale"
    @wheel.prevent="onWheel"
  >
      <svg :viewBox="viewBox" class="flow-svg" :style="{ transform: `scale(${scale})` }">
      <!-- 箭头定义 -->
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="var(--text2)" />
        </marker>
      </defs>

      <!-- 连线 -->
      <g class="edges">
        <path
          v-for="(edge, index) in edges"
          :key="index"
          :d="getEdgePath(edge)"
          class="edge-line"
          marker-end="url(#arrowhead)"
        />
      </g>

      <!-- 节点 -->
      <g
        v-for="node in layoutNodes"
        :key="node.id"
        class="node graph-node"
        :transform="`translate(${node.x || 0}, ${node.y || 0})`"
        @click="emit('node-click', node)"
      >
        <rect
          x="0"
          y="0"
          width="120"
          height="50"
          rx="6"
          :fill="node.id === currentNode ? 'var(--blue-light)' : 'var(--card)'"
          :stroke="getNodeColor(node)"
          stroke-width="2"
        />
        <text
          x="60"
          y="20"
          text-anchor="middle"
          class="node-icon"
          :fill="getNodeColor(node)"
        >
          {{ getNodeIcon(node.type) }}
        </text>
        <text
          x="60"
          y="38"
          text-anchor="middle"
          class="node-label"
        >
          {{ node.label }}
        </text>
      </g>
    </svg>

    <!-- 只读提示 -->
    <div class="readonly-badge">只读视图</div>
  </div>
</template>

<style lang="scss" scoped>
.trace-graph {
  position: relative;
  width: 100%;
  background-color: var(--hover);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
}

.flow-svg {
  width: 100%;
  height: 100%;
}

.edge-line {
  fill: none;
  stroke: var(--text2);
  stroke-width: 2;
}

.node-icon {
  font-size: 14px;
}

.node-label {
  font-size: 12px;
  fill: var(--text);
}

.readonly-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--text2);
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: 4px;
}

// 移动端
.trace-graph--mobile {
  .readonly-badge {
    font-size: 10px;
    padding: 2px 6px;
  }
}
</style>
