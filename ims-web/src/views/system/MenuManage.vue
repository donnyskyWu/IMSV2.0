<script setup lang="ts">
/** 菜单管理（FP-B2-M） */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import { ApiError } from '@/api/request'
import { systemAdminApi } from '@/api/system-admin'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const rows = ref<Record<string, unknown>[]>([])
const keyword = ref('')
const menuType = ref('')
const error = ref('')
const open = ref(false)
const builtin = ref(false)
const form = ref({ name: '', type: 'BUTTON', path: '', permCode: '', visible: true })

const columns: TableColumn[] = [
  { key: 'name', label: '名称' },
  { key: 'typeText', label: '类型' },
  { key: 'path', label: '路由' },
  { key: 'permCode', label: '权限码' },
  { key: 'visibleText', label: '可见' },
  { key: 'builtinText', label: '内置标记' },
  { key: 'actions', label: '操作' },
]

function flatten(nodes: Record<string, unknown>[], acc: Record<string, unknown>[] = []) {
  for (const node of nodes) {
    acc.push({
      ...node,
      typeText: node.type === 'DIR' ? '目录' : node.type === 'BUTTON' ? '按钮' : '菜单',
      visibleText: node.visible === false || node.visible === 0 ? '隐藏' : '可见',
      builtinText: node.isBuiltin ? '内置' : '',
    })
    const children = node.children as Record<string, unknown>[] | undefined
    if (children?.length) flatten(children, acc)
  }
  return acc
}

async function load() {
  const tree = await systemAdminApi.menuTree({ type: menuType.value, keyword: keyword.value })
  rows.value = flatten(tree || []).filter((row) => !menuType.value || row.type === menuType.value)
}

async function save() {
  error.value = ''
  if (form.value.permCode && !/^ims(:[a-z][a-z0-9-]*){2,3}$/.test(form.value.permCode)) {
    error.value = '权限码格式错误'
    return
  }
  try {
    await systemAdminApi.menuCreate(form.value)
    toast.success('保存成功')
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败'
    throw err
  }
}

async function hideRow(row: Record<string, unknown>) {
  await systemAdminApi.menuUpdate({ id: row.id, visible: false, name: row.name })
  toast.success('已隐藏')
  await load()
}

async function remove(row: Record<string, unknown>) {
  try {
    await systemAdminApi.menuDelete(String(row.id))
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '删除失败'
  }
}

function edit(row: Record<string, unknown>) {
  builtin.value = Boolean(row.isBuiltin)
  form.value = {
    name: String(row.name || ''),
    type: String(row.type || 'MENU'),
    path: String(row.path || ''),
    permCode: String(row.permCode || ''),
    visible: row.visible !== false,
  }
  open.value = true
}

onMounted(load)
</script>

<template>
  <div data-testid="page-menu">
    <PageHeader title="菜单" />
    <div class="toolbar">
      <select v-model="menuType" data-testid="menu-type" @change="load">
        <option value="">全部</option>
        <option value="DIR">目录</option>
        <option value="MENU">菜单</option>
        <option value="BUTTON">按钮</option>
      </select>
      <input v-model="keyword" data-testid="menu-keyword" placeholder="关键字" @change="load" />
      <el-button data-testid="btn-menu-create" type="primary" @click="builtin = false; open = true">新建菜单</el-button>
    </div>
    <p v-if="error" class="error" data-testid="menu-error">{{ error }}</p>
    <PlainTable :columns="columns" :data="rows">
      <template #cell-actions="{ row }">
        <el-button data-testid="btn-menu-edit" @click="edit(row)">编辑</el-button>
        <el-button data-testid="btn-menu-hide" @click="hideRow(row)">隐藏</el-button>
        <el-button data-testid="btn-menu-delete" @click="remove(row)">删除</el-button>
      </template>
    </PlainTable>
    <FormDrawer v-model:open="open" title="菜单" :submit="save">
      <p v-if="error" class="error">{{ error }}</p>
      <label>名称<input v-model="form.name" data-testid="field-menu-name" /></label>
      <label>路由<input v-model="form.path" data-testid="field-menu-path" :readonly="builtin" /></label>
      <label>权限码<input v-model="form.permCode" data-testid="field-menu-perm" :readonly="builtin" /></label>
    </FormDrawer>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.error {
  color: var(--danger, #c45656);
}

label {
  display: block;
  margin: 8px 0;
}
</style>
