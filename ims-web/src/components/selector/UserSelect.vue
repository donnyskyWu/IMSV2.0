<script setup lang="ts">
/**
 * UserSelect 用户选择器
 * 依据: FP-C15-03
 * 派生自 RemoteSelect，使用模拟数据
 */
import { ref } from 'vue'
import RemoteSelect from './RemoteSelect.vue'

interface Props {
  modelValue?: string | number | Array<string | number>
  placeholder?: string
  multiple?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '选择用户',
  multiple: false,
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | number | Array<string | number> | undefined): void
  (e: 'change', val: unknown, option: unknown): void
}>()

// 模拟用户数据
const mockUsers = [
  { value: 1, label: '张三', dept: '技术部' },
  { value: 2, label: '李四', dept: '产品部' },
  { value: 3, label: '王五', dept: '设计部' },
  { value: 4, label: '赵六', dept: '技术部' },
  { value: 5, label: '钱七', dept: '市场部' },
  { value: 6, label: '孙八', dept: '运营部' },
  { value: 7, label: '周九', dept: '财务部' },
  { value: 8, label: '吴十', dept: '人事部' },
  { value: 9, label: '郑十一', dept: '技术部' },
  { value: 10, label: '陈十二', dept: '产品部' },
]

// 搜索函数
async function fetchUsers(params: { keyword: string; pageNo: number; pageSize: number }) {
  await new Promise((r) => setTimeout(r, 200))
  
  let filtered = mockUsers
  if (params.keyword) {
    filtered = mockUsers.filter(
      (u) => u.label.includes(params.keyword) || u.dept.includes(params.keyword)
    )
  }

  const start = (params.pageNo - 1) * params.pageSize
  const list = filtered.slice(start, start + params.pageSize)

  return { list, total: filtered.length }
}

// 回显函数
async function echoUsers(value: string | number | Array<string | number>) {
  await new Promise((r) => setTimeout(r, 100))
  
  const values = Array.isArray(value) ? value : [value]
  return mockUsers.filter((u) => values.includes(u.value))
}

function handleUpdate(val: string | number | Array<string | number> | undefined) {
  emit('update:modelValue', val)
}

function handleChange(val: unknown, option: unknown) {
  emit('change', val, option)
}
</script>

<template>
  <RemoteSelect
    :model-value="modelValue"
    :placeholder="placeholder"
    :multiple="multiple"
    :disabled="disabled"
    :fetch-fn="fetchUsers"
    :echo-fn="echoUsers"
    @update:model-value="handleUpdate"
    @change="handleChange"
  >
    <template #option="{ option }">
      <div class="user-option">
        <span class="user-name">{{ option.label }}</span>
        <span class="user-dept">{{ option.dept }}</span>
      </div>
    </template>
  </RemoteSelect>
</template>

<style lang="scss" scoped>
.user-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.user-name {
  color: var(--text);
}

.user-dept {
  font-size: 12px;
  color: var(--text2);
}
</style>
