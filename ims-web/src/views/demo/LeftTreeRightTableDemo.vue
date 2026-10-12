<script setup lang="ts">
/**
 * 左树右表演示 (VC-L03)
 * 部门树 + 人员表：含下级、待分配、停用部门不带入、浏览器历史同步。
 */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import LeftTreeRightTable from '@/components/list/LeftTreeRightTable.vue'
import Pagination from '@/components/list/Pagination.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'

interface TreeNode {
  id: string
  label: string
  disabled?: boolean
  children?: TreeNode[]
}

interface Person {
  id: string
  name: string
  primary: string
  deptIds: string[]
}

const route = useRoute()
const router = useRouter()

const showDisabled = ref(false)
const includeChildren = ref(true)
const pageNo = ref(1)
const pageSize = ref(10)
const drawerOpen = ref(false)
const deptField = ref('')

const baseTree: TreeNode[] = [
  {
    id: 'all',
    label: '全部',
    children: [
      { id: 'unassigned', label: '待分配' },
      {
        id: 'market',
        label: '市场部',
        children: [
          { id: 'm1', label: '市场一组' },
          { id: 'm2', label: '市场二组' },
        ],
      },
      { id: 'tech', label: '技术部' },
      {
        id: 'ops',
        label: '运营部',
        children: [{ id: 'live', label: '直播运营组' }],
      },
      { id: 'old', label: '旧项目组', disabled: true },
    ],
  },
]

const people: Person[] = [
  { id: 'p1', name: '张一', primary: 'market', deptIds: ['market'] },
  { id: 'p2', name: '张二', primary: 'market', deptIds: ['market'] },
  { id: 'p3', name: '王五', primary: 'market', deptIds: ['market', 'm1'] },
  { id: 'p4', name: '甲一', primary: 'm1', deptIds: ['m1'] },
  { id: 'p5', name: '甲二', primary: 'm1', deptIds: ['m1'] },
  { id: 'p6', name: '甲三', primary: 'm1', deptIds: ['m1'] },
  { id: 'p7', name: '乙一', primary: 'm2', deptIds: ['m2'] },
  { id: 'p8', name: '乙二', primary: 'm2', deptIds: ['m2'] },
  { id: 'p9', name: '乙三', primary: 'm2', deptIds: ['m2'] },
  { id: 'p10', name: '技一', primary: 'tech', deptIds: ['tech'] },
  { id: 'p11', name: '运一', primary: 'ops', deptIds: ['ops'] },
  { id: 'p12', name: '运二', primary: 'ops', deptIds: ['ops'] },
  { id: 'p13', name: '播一', primary: 'live', deptIds: ['live'] },
  { id: 'p14', name: '播二', primary: 'live', deptIds: ['live'] },
  { id: 'p15', name: '待一', primary: 'unassigned', deptIds: ['unassigned'] },
  { id: 'p16', name: '待二', primary: 'unassigned', deptIds: ['unassigned'] },
]

const selectedCategory = ref('all')

const treeData = computed(() => {
  function walk(nodes: TreeNode[]): TreeNode[] {
    return nodes
      .filter((node) => showDisabled.value || !node.disabled)
      .map((node) => ({
        ...node,
        children: node.children ? walk(node.children) : undefined,
      }))
  }
  return walk(baseTree)
})

function findNode(nodes: TreeNode[], id: string): TreeNode | null {
  for (const node of nodes) {
    if (node.id === id) return node
    if (node.children) {
      const found = findNode(node.children, id)
      if (found) return found
    }
  }
  return null
}

function collectIds(id: string, include: boolean): string[] {
  const node = findNode(baseTree, id)
  if (!node) return [id]
  const ids = [node.id]
  if (include && node.children) {
    for (const child of node.children) ids.push(...collectIds(child.id, true))
  }
  return ids
}

const filtered = computed(() => {
  const id = selectedCategory.value || 'all'
  if (id === 'all') return people
  if (includeChildren.value) {
    const ids = collectIds(id, true)
    return people.filter((person) => person.deptIds.some((dept) => ids.includes(dept)))
  }
  return people.filter((person) => person.primary === id)
})

const tableData = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

const showInclude = computed(() => selectedCategory.value !== 'all' && selectedCategory.value !== 'unassigned')

function syncFromRoute() {
  const dept = String(route.query.dept || 'all')
  selectedCategory.value = dept
  includeChildren.value = route.query.include === '0' ? false : true
}

watch(() => route.query.dept, () => {
  pageNo.value = 1
  syncFromRoute()
}, { immediate: true })

watch(() => route.query.include, syncFromRoute)

function handleCategoryChange(node: { id: string }) {
  pageNo.value = 1
  router.push({
    query: {
      dept: node.id,
      include: includeChildren.value ? '1' : '0',
    },
  })
}

function onIncludeChange() {
  pageNo.value = 1
  router.replace({
    query: {
      ...route.query,
      dept: selectedCategory.value,
      include: includeChildren.value ? '1' : '0',
    },
  })
}

const deptOptions = [
  { label: '市场部', value: 'market' },
  { label: '市场一组', value: 'm1' },
  { label: '技术部', value: 'tech' },
  { label: '运营部', value: 'ops' },
  { label: '旧项目组', value: 'old', disabled: true },
]

function handleCreate() {
  const current = findNode(baseTree, selectedCategory.value)
  if (!current || current.id === 'all' || current.disabled) {
    deptField.value = ''
  } else {
    deptField.value = current.id
  }
  drawerOpen.value = true
}
</script>

<template>
  <AppLayout>
    <div class="left-tree-right-table-demo">
      <PageHeader title="左树右表演示" sub-title="FP-P-11 / UI-L02">
        <template #actions>
          <el-button v-perm="'ims:demo:order:create'" type="primary" @click="handleCreate">新建人员</el-button>
          <el-checkbox v-model="showDisabled">显示停用部门</el-checkbox>
        </template>
      </PageHeader>

      <LeftTreeRightTable
        v-model:selected-key="selectedCategory"
        :tree-data="treeData"
        tree-placeholder="搜索部门"
        @node-click="handleCategoryChange"
      >
        <div class="table-section">
          <div v-if="showInclude" class="include-row">
            <span>含下级</span>
            <el-switch v-model="includeChildren" @change="onIncludeChange" />
          </div>
          <div class="table-wrap">
            <el-table :data="tableData" style="width: 100%">
              <el-table-column prop="name" label="姓名" min-width="120" />
              <el-table-column prop="primary" label="部门" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default>
                  <el-button v-perm="'ims:demo:order:update'" text type="primary" size="small">编辑</el-button>
                  <el-button v-perm="'ims:demo:order:delete'" text type="primary" size="small">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <Pagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="filtered.length" />
        </div>
      </LeftTreeRightTable>

      <FormDrawer v-model:open="drawerOpen" title="新建人员" size="M">
        <el-form label-width="90px">
          <el-form-item label="姓名">
            <el-input placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="所属部门">
            <el-select v-model="deptField" placeholder="请选择" clearable style="width: 100%">
              <el-option
                v-for="opt in deptOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
                :disabled="opt.disabled"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </FormDrawer>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.left-tree-right-table-demo {
  width: 100%;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.table-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.include-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-wrap {
  flex: 1;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  overflow: hidden;
}
</style>
