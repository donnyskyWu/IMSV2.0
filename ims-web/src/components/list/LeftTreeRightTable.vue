<script setup lang="ts">
/**
 * LeftTreeRightTable 左树右表布局
 * 依据: FP-C-31, 00-工作包 §2.1 Q12, §2.2 #1
 * 桌面: 左树 280px，右边表格
 * 手机 (Q12): 树收进抽屉，顶部显示已选节点和切换按钮
 */
import { ref, computed, watch } from 'vue'
import { Menu, Close } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'
import type { TreeNode } from '@/types'

interface Props {
  treeData: TreeNode[]
  selectedKey?: string | number
  treePlaceholder?: string
  treeWidth?: number
}

const props = withDefaults(defineProps<Props>(), {
  selectedKey: '',
  treePlaceholder: '搜索',
  treeWidth: 280,
})

const emit = defineEmits<{
  (e: 'update:selectedKey', key: string | number): void
  (e: 'node-click', node: TreeNode, nodeData: TreeNode): void
}>()

const { isMobile } = useResponsive()

// 移动端抽屉
const drawerVisible = ref(false)

// 搜索关键词
const searchKeyword = ref('')

// 展开的节点
const expandedKeys = ref<(string | number)[]>([])

// 默认展开所有一级节点
watch(
  () => props.treeData,
  (data) => {
    if (data.length > 0 && expandedKeys.value.length === 0) {
      expandedKeys.value = data.map((n) => n.id)
    }
  },
  { immediate: true }
)

// 当前选中节点名称
const selectedNodeLabel = computed(() => {
  if (!props.selectedKey) return '全部'
  const findNode = (nodes: TreeNode[]): string => {
    for (const node of nodes) {
      if (node.id === props.selectedKey) return node.label
      if (node.children?.length) {
        const found = findNode(node.children)
        if (found) return found
      }
    }
    return ''
  }
  return findNode(props.treeData) || '全部'
})

// 过滤树
function filterNode(value: string, data: TreeNode): boolean {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

// 点击节点
function handleNodeClick(data: TreeNode, node: unknown) {
  emit('update:selectedKey', data.id)
  emit('node-click', data, node as TreeNode)
  if (isMobile.value) {
    drawerVisible.value = false
  }
}

// 清除选择
function clearSelection() {
  emit('update:selectedKey', '')
}
</script>

<template>
  <div class="left-tree-right-table" :class="{ mobile: isMobile }">
    <!-- 桌面端: 左侧树 -->
    <aside
      v-if="!isMobile"
      class="tree-panel"
      :style="{ width: `${treeWidth}px` }"
    >
      <div class="tree-header">
        <el-input
          v-model="searchKeyword"
          :placeholder="treePlaceholder"
          clearable
          size="small"
        >
          <template #prefix>
            <el-icon>
              <svg viewBox="0 0 24 24" width="14" height="14">
                <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
              </svg>
            </el-icon>
          </template>
        </el-input>
      </div>
      <div class="tree-body">
        <el-tree
          :data="treeData"
          :props="{ label: 'label', children: 'children' }"
          :filter-node-method="filterNode"
          :default-expanded-keys="expandedKeys"
          :current-node-key="selectedKey"
          node-key="id"
          highlight-current
          @node-click="handleNodeClick"
        >
          <template #default="{ node, data }">
            <span class="tree-node">
              <span class="tree-node__label">{{ node.label }}</span>
              <el-badge
                v-if="data.count !== undefined"
                :value="data.count"
                :max="999"
                type="info"
              />
            </span>
          </template>
        </el-tree>
      </div>
    </aside>

    <!-- 移动端: 顶部选择栏 (Q12) -->
    <div v-if="isMobile" class="mobile-tree-bar">
      <div class="selected-node" @click="drawerVisible = true">
        <el-icon><Menu /></el-icon>
        <span class="node-label">{{ selectedNodeLabel }}</span>
      </div>
      <el-button
        v-if="selectedKey"
        text
        size="small"
        @click.stop="clearSelection"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <!-- 移动端: 树抽屉 (100% 高度) -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      size="280"
      :show-close="true"
      title="选择分类"
    >
      <div class="tree-header">
        <el-input
          v-model="searchKeyword"
          :placeholder="treePlaceholder"
          clearable
          size="small"
        >
          <template #prefix>
            <el-icon>
              <svg viewBox="0 0 24 24" width="14" height="14">
                <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
              </svg>
            </el-icon>
          </template>
        </el-input>
      </div>
      <el-tree
        :data="treeData"
        :props="{ label: 'label', children: 'children' }"
        :filter-node-method="filterNode"
        :default-expanded-keys="expandedKeys"
        :current-node-key="selectedKey"
        node-key="id"
        highlight-current
        @node-click="handleNodeClick"
      >
        <template #default="{ node, data }">
          <span class="tree-node">
            <span class="tree-node__label">{{ node.label }}</span>
            <el-badge
              v-if="data.count !== undefined"
              :value="data.count"
              :max="999"
              type="info"
            />
          </span>
        </template>
      </el-tree>
    </el-drawer>

    <!-- 右侧内容 -->
    <main class="table-panel">
      <slot />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.left-tree-right-table {
  display: flex;
  height: 100%;
  gap: 16px;

  &.mobile {
    flex-direction: column;
    gap: 0;
  }
}

.tree-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
}

.tree-header {
  padding: 12px;
  border-bottom: 1px solid var(--line);
}

.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;

  &__label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.table-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

// 移动端选择栏
.mobile-tree-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  margin-bottom: 12px;

  .selected-node {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    min-height: 44px;
    padding: 0 4px;
    margin: 0 -4px;
  }

  .node-label {
    font-weight: 500;
    color: var(--text);
  }
}
</style>
