<script setup lang="ts">
/**
 * RoleSelect 角色选择器
 * 依据: FP-C15-05
 */
import RemoteSelect from './RemoteSelect.vue'

interface Props {
  modelValue?: string | number | Array<string | number>
  placeholder?: string
  multiple?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '选择角色',
  multiple: false,
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | number | Array<string | number> | undefined): void
  (e: 'change', val: unknown, option: unknown): void
}>()

// 模拟角色数据
const mockRoles = [
  { value: 1, label: '超级管理员', code: 'super_admin' },
  { value: 2, label: '系统管理员', code: 'admin' },
  { value: 3, label: '部门经理', code: 'dept_manager' },
  { value: 4, label: '普通员工', code: 'employee' },
  { value: 5, label: '财务专员', code: 'finance' },
  { value: 6, label: '人事专员', code: 'hr' },
  { value: 7, label: '审核员', code: 'auditor' },
  { value: 8, label: '访客', code: 'guest' },
]

async function fetchRoles(params: { keyword: string; pageNo: number; pageSize: number }) {
  await new Promise((r) => setTimeout(r, 150))
  
  let filtered = mockRoles
  if (params.keyword) {
    filtered = mockRoles.filter(
      (r) => r.label.includes(params.keyword) || r.code.includes(params.keyword)
    )
  }

  const start = (params.pageNo - 1) * params.pageSize
  const list = filtered.slice(start, start + params.pageSize)

  return { list, total: filtered.length }
}

async function echoRoles(value: string | number | Array<string | number>) {
  await new Promise((r) => setTimeout(r, 100))
  
  const values = Array.isArray(value) ? value : [value]
  return mockRoles.filter((r) => values.includes(r.value))
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
    :fetch-fn="fetchRoles"
    :echo-fn="echoRoles"
    @update:model-value="handleUpdate"
    @change="handleChange"
  >
    <template #option="{ option }">
      <div class="role-option">
        <span class="role-name">{{ option.label }}</span>
        <span class="role-code">{{ option.code }}</span>
      </div>
    </template>
  </RemoteSelect>
</template>

<style lang="scss" scoped>
.role-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.role-name {
  color: var(--text);
}

.role-code {
  font-size: 12px;
  color: var(--text2);
  font-family: 'SF Mono', Monaco, Consolas, monospace;
}
</style>
