<script setup lang="ts">
/**
 * DeptTreeSelect 部门树选择器
 * 依据: FP-C15-04
 * 树形下拉选择，支持搜索
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useResponsive } from '@/utils/responsive'

interface TreeNode {
  id: string | number
  label: string
  children?: TreeNode[]
}

interface Props {
  modelValue?: string | number | Array<string | number>
  placeholder?: string
  multiple?: boolean
  disabled?: boolean
  checkStrictly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '选择部门',
  multiple: false,
  disabled: false,
  checkStrictly: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | number | Array<string | number> | undefined): void
  (e: 'change', val: string | number | Array<string | number> | undefined, node: TreeNode | TreeNode[] | undefined): void
}>()

const { isMobile } = useResponsive()

// 模拟部门树数据
const deptTree = ref<TreeNode[]>([
  {
    id: 900,
    label: '星河传媒',
    children: [
      {
        id: 901,
        label: '市场部',
        children: [{ id: 902, label: '星河传媒 / 市场部 / 市场一组' }],
      },
    ],
  },
  {
    id: 1,
    label: '总公司',
    children: [
      {
        id: 11,
        label: '技术中心',
        children: [
          { id: 111, label: '研发一部' },
          { id: 112, label: '研发二部' },
          { id: 113, label: '测试部' },
        ],
      },
      {
        id: 12,
        label: '产品中心',
        children: [
          { id: 121, label: '产品一部' },
          { id: 122, label: '产品二部' },
        ],
      },
      {
        id: 13,
        label: '运营中心',
        children: [
          { id: 131, label: '市场部' },
          { id: 132, label: '客服部' },
        ],
      },
      { id: 14, label: '财务部' },
      { id: 15, label: '人力资源部' },
    ],
  },
])

// 树配置
const treeProps = {
  value: 'id',
  label: 'label',
  children: 'children',
}

// 搜索过滤
function filterNode(value: string, data: TreeNode): boolean {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

function handleChange(val: string | number | Array<string | number> | undefined) {
  emit('update:modelValue', val)
  // 可以从树中查找节点，暂时简化处理
  emit('change', val, undefined)
}
</script>

<template>
  <el-tree-select
    :model-value="modelValue"
    :data="deptTree"
    :props="treeProps"
    :placeholder="placeholder"
    :multiple="multiple"
    :disabled="disabled"
    :check-strictly="checkStrictly"
    :render-after-expand="false"
    :filter-node-method="filterNode"
    filterable
    clearable
    class="dept-tree-select"
    :class="{ 'dept-tree-select--mobile': isMobile }"
    @update:model-value="handleChange"
  />
</template>

<style lang="scss" scoped>
.dept-tree-select {
  width: 100%;
}

// 移动端
.dept-tree-select--mobile {
  :deep(.el-select__wrapper) {
    min-height: var(--min-touch-size);
  }
}
</style>
