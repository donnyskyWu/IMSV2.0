<script setup lang="ts">
/**
 * DeptTree 部门树 (UI-C42)
 * 依据: FP-C-42
 * - 搜索过滤
 * - CRUD 操作
 * - 拖拽移动
 * - 来源标识 (本地/钉钉)
 * - 钉钉同步模拟
 */
import { ref, computed, watch } from 'vue'
import {
  Search,
  Plus,
  Edit,
  Delete,
  Rank,
  Refresh,
  MoreFilled,
  OfficeBuilding,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/utils/responsive'
import FormDrawer from '@/components/form/FormDrawer.vue'
import ConfirmDialog from '@/components/form/ConfirmDialog.vue'

interface DeptNode {
  id: string | number
  name: string
  parentId?: string | number
  source?: 'local' | 'dingtalk'
  sort?: number
  status?: 0 | 1
  children?: DeptNode[]
  count?: number
}

interface Props {
  data: DeptNode[]
  selectedKey?: string | number
  allowEdit?: boolean
  allowDrag?: boolean
  showCount?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  allowEdit: true,
  allowDrag: true,
  showCount: true,
})

const emit = defineEmits<{
  (e: 'update:selectedKey', key: string | number): void
  (e: 'select', node: DeptNode): void
  (e: 'add', parentId: string | number | undefined): void
  (e: 'edit', node: DeptNode): void
  (e: 'delete', node: DeptNode): void
  (e: 'move', node: DeptNode, targetNode: DeptNode, position: 'before' | 'after' | 'inner'): void
  (e: 'sync'): void
}>()

const { isMobile } = useResponsive()

// 搜索关键词
const searchKeyword = ref('')

// 展开的节点
const expandedKeys = ref<(string | number)[]>([])

// 编辑抽屉
const editDrawerVisible = ref(false)
const editingNode = ref<DeptNode | null>(null)
const isAdding = ref(false)
const addParentId = ref<string | number | undefined>()

// 删除确认
const deleteConfirmVisible = ref(false)
const deletingNode = ref<DeptNode | null>(null)

// 同步状态
const syncing = ref(false)

// 树配置
const treeProps = {
  label: 'name',
  children: 'children',
}

// 默认展开一级
watch(
  () => props.data,
  (data) => {
    if (data.length > 0 && expandedKeys.value.length === 0) {
      expandedKeys.value = data.map((n) => n.id)
    }
  },
  { immediate: true }
)

// 搜索过滤
function filterNode(value: string, data: DeptNode): boolean {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

// 选中节点
function handleNodeClick(data: DeptNode) {
  emit('update:selectedKey', data.id)
  emit('select', data)
}

// 新增部门
function handleAdd(parentId?: string | number) {
  isAdding.value = true
  addParentId.value = parentId
  editingNode.value = {
    id: '',
    name: '',
    parentId,
    source: 'local',
    status: 1,
    sort: 0,
  }
  editDrawerVisible.value = true
}

// 编辑部门
function handleEdit(node: DeptNode) {
  isAdding.value = false
  editingNode.value = { ...node }
  editDrawerVisible.value = true
}

// 删除部门
function handleDelete(node: DeptNode) {
  if (node.children && node.children.length > 0) {
    ElMessage.warning('该部门下有子部门，无法删除')
    return
  }
  deletingNode.value = node
  deleteConfirmVisible.value = true
}

// 确认删除
function confirmDelete() {
  if (deletingNode.value) {
    emit('delete', deletingNode.value)
    ElMessage.success('删除成功')
  }
  deleteConfirmVisible.value = false
  deletingNode.value = null
}

// 保存编辑
function handleSave() {
  if (!editingNode.value?.name) {
    ElMessage.warning('请输入部门名称')
    return
  }
  if (isAdding.value) {
    emit('add', addParentId.value)
  } else {
    emit('edit', editingNode.value)
  }
  ElMessage.success(isAdding.value ? '新增成功' : '保存成功')
  editDrawerVisible.value = false
  editingNode.value = null
}

// 拖拽判断
function allowDrop(
  draggingNode: { data: DeptNode },
  dropNode: { data: DeptNode },
  type: 'prev' | 'inner' | 'next'
): boolean {
  // 钉钉来源的部门不能拖拽到其他位置
  if (draggingNode.data.source === 'dingtalk') return false
  // 不能拖拽到钉钉部门下
  if (type === 'inner' && dropNode.data.source === 'dingtalk') return false
  return true
}

// 拖拽完成
function handleDrop(
  draggingNode: { data: DeptNode },
  dropNode: { data: DeptNode },
  dropType: 'before' | 'after' | 'inner'
) {
  emit('move', draggingNode.data, dropNode.data, dropType)
  ElMessage.success('移动成功')
}

// 钉钉同步
async function handleSync() {
  syncing.value = true
  // 模拟同步
  await new Promise((r) => setTimeout(r, 2000))
  syncing.value = false
  emit('sync')
  ElMessage.success('同步完成')
}

// 右键菜单命令
function handleCommand(command: string, node: DeptNode) {
  switch (command) {
    case 'add':
      handleAdd(node.id)
      break
    case 'edit':
      handleEdit(node)
      break
    case 'delete':
      handleDelete(node)
      break
  }
}
</script>

<template>
  <div class="dept-tree" :class="{ 'dept-tree--mobile': isMobile }">
    <!-- 工具栏 -->
    <div class="tree-toolbar">
      <el-input
        v-model="searchKeyword"
        :placeholder="'搜索部门'"
        clearable
        size="small"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div class="toolbar-actions">
        <el-button
          v-if="allowEdit"
          size="small"
          type="primary"
          @click="handleAdd()"
        >
          <el-icon><Plus /></el-icon>
          新增
        </el-button>
        <el-button
          size="small"
          :loading="syncing"
          @click="handleSync"
        >
          <el-icon><Refresh /></el-icon>
          同步
        </el-button>
      </div>
    </div>

    <!-- 树 -->
    <div class="tree-body">
      <el-tree
        :data="data"
        :props="treeProps"
        :filter-node-method="filterNode"
        :default-expanded-keys="expandedKeys"
        :current-node-key="selectedKey"
        :draggable="allowDrag && !isMobile"
        :allow-drop="allowDrop"
        node-key="id"
        highlight-current
        @node-click="handleNodeClick"
        @node-drop="handleDrop"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-content">
              <el-icon class="node-icon"><OfficeBuilding /></el-icon>
              <span class="node-name">{{ data.name }}</span>
              
              <!-- 来源标识 -->
              <el-tag
                v-if="data.source === 'dingtalk'"
                size="small"
                type="info"
                class="source-tag"
              >
                钉钉
              </el-tag>

              <!-- 人数 -->
              <span v-if="showCount && data.count !== undefined" class="node-count">
                ({{ data.count }})
              </span>
            </div>

            <!-- 操作按钮 -->
            <el-dropdown
              v-if="allowEdit"
              trigger="click"
              @command="(cmd: string) => handleCommand(cmd, data)"
              @click.stop
            >
              <el-button
                text
                size="small"
                class="more-btn touch-target"
                @click.stop
              >
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="add">
                    <el-icon><Plus /></el-icon>
                    添加子部门
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="edit"
                    :disabled="data.source === 'dingtalk'"
                  >
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-dropdown-item>
                  <el-dropdown-item
                    command="delete"
                    :disabled="data.source === 'dingtalk' || (data.children && data.children.length > 0)"
                  >
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- 编辑抽屉 -->
    <FormDrawer
      v-model="editDrawerVisible"
      :title="isAdding ? '新增部门' : '编辑部门'"
      @submit="handleSave"
    >
      <el-form v-if="editingNode" label-width="80px">
        <el-form-item label="部门名称" required>
          <el-input v-model="editingNode.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editingNode.sort" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="editingNode.status"
            :active-value="1"
            :inactive-value="0"
          />
        </el-form-item>
      </el-form>
    </FormDrawer>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="deleteConfirmVisible"
      title="删除确认"
      :content="`确定要删除部门「${deletingNode?.name}」吗？`"
      type="danger"
      @confirm="confirmDelete"
    />
  </div>
</template>

<style lang="scss" scoped>
.dept-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
}

.tree-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-bottom: 1px solid var(--line);

  .el-input {
    flex: 1;
  }

  .toolbar-actions {
    display: flex;
    gap: 8px;
  }
}

.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.node-icon {
  color: var(--blue);
  font-size: 14px;
}

.node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-tag {
  margin-left: 4px;
  font-size: 10px;
  height: 18px;
  padding: 0 4px;
}

.node-count {
  font-size: 12px;
  color: var(--text2);
}

.more-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.tree-node:hover .more-btn {
  opacity: 1;
}

// 移动端
.dept-tree--mobile {
  .tree-toolbar {
    flex-wrap: wrap;
    gap: 8px;

    .el-input {
      width: 100%;
    }

    .toolbar-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }

  .more-btn {
    opacity: 1;
  }
}
</style>
