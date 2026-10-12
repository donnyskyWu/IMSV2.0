<script setup lang="ts">
/**
 * 部门树演示页 (FP-P-10)
 * 依据: UI-C42
 * 包含: 搜索、CRUD、拖拽移动、来源标识、钉钉同步
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import DeptTree from '@/components/dept/DeptTree.vue'

// 模拟部门数据
const deptData = ref([
  {
    id: 1,
    name: '总公司',
    source: 'local' as const,
    count: 156,
    children: [
      {
        id: 11,
        name: '技术中心',
        source: 'local' as const,
        count: 45,
        children: [
          { id: 111, name: '研发一部', source: 'local' as const, count: 18 },
          { id: 112, name: '研发二部', source: 'dingtalk' as const, count: 15 },
          { id: 113, name: '测试部', source: 'local' as const, count: 12 },
        ],
      },
      {
        id: 12,
        name: '产品中心',
        source: 'dingtalk' as const,
        count: 28,
        children: [
          { id: 121, name: '产品一部', source: 'dingtalk' as const, count: 15 },
          { id: 122, name: '产品二部', source: 'dingtalk' as const, count: 13 },
        ],
      },
      {
        id: 13,
        name: '运营中心',
        source: 'local' as const,
        count: 35,
        children: [
          { id: 131, name: '市场部', source: 'local' as const, count: 20 },
          { id: 132, name: '客服部', source: 'local' as const, count: 15 },
        ],
      },
      { id: 14, name: '财务部', source: 'local' as const, count: 12 },
      { id: 15, name: '人力资源部', source: 'dingtalk' as const, count: 8 },
    ],
  },
])

// 选中的部门
const selectedKey = ref<string | number>('')

// 事件日志
const eventLogs = ref<string[]>([])

function logEvent(message: string) {
  const time = new Date().toLocaleTimeString()
  eventLogs.value.unshift(`[${time}] ${message}`)
  if (eventLogs.value.length > 10) {
    eventLogs.value.pop()
  }
}

// 选中部门
function handleSelect(node: { name: string }) {
  logEvent(`选中部门: ${node.name}`)
}

// 新增
function handleAdd(parentId: string | number | undefined) {
  logEvent(`新增子部门，父级ID: ${parentId ?? '根'}`)
}

// 编辑
function handleEdit(node: { name: string }) {
  logEvent(`编辑部门: ${node.name}`)
}

// 删除
function handleDelete(node: { name: string }) {
  logEvent(`删除部门: ${node.name}`)
}

// 移动
function handleMove(
  node: { name: string },
  targetNode: { name: string },
  position: 'before' | 'after' | 'inner'
) {
  logEvent(`移动部门「${node.name}」到「${targetNode.name}」的 ${position}`)
}

// 同步
function handleSync() {
  logEvent('触发钉钉同步')
}
</script>

<template>
  <AppLayout>
    <div class="dept-tree-demo">
      <PageHeader title="部门树演示" sub-title="FP-P-10 / UI-C42" />

      <div class="demo-content">
        <div class="tree-panel">
          <h3 class="panel-title">部门组织架构</h3>
          <DeptTree
            v-model:selected-key="selectedKey"
            :data="deptData"
            :allow-edit="true"
            :allow-drag="true"
            :show-count="true"
            @select="handleSelect"
            @add="handleAdd"
            @edit="handleEdit"
            @delete="handleDelete"
            @move="handleMove"
            @sync="handleSync"
          />
        </div>

        <div class="info-panel">
          <h3 class="panel-title">功能说明</h3>
          <div class="feature-list">
            <div class="feature-item">
              <span class="feature-icon">🔍</span>
              <span>搜索过滤：支持按部门名称搜索</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">➕</span>
              <span>新增：点击节点菜单可添加子部门</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">✏️</span>
              <span>编辑：本地部门可编辑，钉钉部门不可编辑</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🗑️</span>
              <span>删除：无子部门的本地部门可删除</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">↕️</span>
              <span>拖拽：桌面端可拖拽调整位置（移动端不支持）</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🔄</span>
              <span>同步：模拟钉钉组织架构同步</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🏷️</span>
              <span>来源标识：「钉钉」标签表示来自钉钉的部门</span>
            </div>
          </div>

          <h3 class="panel-title" style="margin-top: 24px;">操作日志</h3>
          <div class="event-logs">
            <div v-if="eventLogs.length === 0" class="empty-log">暂无操作</div>
            <div v-for="(log, index) in eventLogs" :key="index" class="log-item">
              {{ log }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.dept-tree-demo {
  width: 100%;
}

.demo-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;

  @media (max-width: 767px) {
    grid-template-columns: 1fr;
  }
}

.tree-panel {
  display: flex;
  flex-direction: column;
  height: 600px;

  @media (max-width: 767px) {
    height: 400px;
  }
}

.info-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.feature-list {
  padding: 16px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--hover);

  &:last-child {
    border-bottom: none;
  }

  .feature-icon {
    font-size: 16px;
  }

  span:last-child {
    font-size: 14px;
    color: var(--text2);
  }
}

.event-logs {
  padding: 16px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  max-height: 200px;
  overflow-y: auto;
}

.empty-log {
  text-align: center;
  color: var(--text2);
  font-size: 14px;
}

.log-item {
  padding: 6px 0;
  font-size: 13px;
  color: var(--text2);
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  border-bottom: 1px solid var(--hover);

  &:last-child {
    border-bottom: none;
  }
}
</style>
