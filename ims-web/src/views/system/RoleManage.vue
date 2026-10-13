<script setup lang="ts">
/** 角色权限（FP-B2-R） */
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import StatCard from '@/components/list/StatCard.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import { ApiError } from '@/api/request'
import { systemAdminApi } from '@/api/system-admin'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const auth = useAuthStore()
const rows = ref<Record<string, unknown>[]>([])
const error = ref('')
const drawer = ref(false)
const form = ref({ code: '', name: '' })
const permOpen = ref(false)
const currentId = ref('')
const checkedMenus = ref<string[]>([])
const writeChecked = ref(false)
const readChecked = ref(false)
const scope = ref('DEPT')
const previewText = ref('')
const members = ref<Record<string, unknown>[]>([])
const memberOpen = ref(false)

const stats = computed(() => {
  const list = rows.value
  return [
    { title: '角色总数', value: list.length },
    { title: '手工', value: list.filter((row) => row.source === 'MANUAL' || row.sourceText === '手工').length },
    { title: '钉钉自动', value: list.filter((row) => row.source === 'DINGTALK_AUTO' || row.sourceText === '钉钉自动').length },
    { title: '待配置', value: list.filter((row) => row.status === 'PENDING_CONFIG' || row.statusText === '待配置').length },
  ]
})

const columns: TableColumn[] = [
  { key: 'roleKey', label: '角色编码' },
  { key: 'name', label: '名称' },
  { key: 'sourceText', label: '来源' },
  { key: 'statusText', label: '状态' },
  { key: 'menuCount', label: '菜单数' },
  { key: 'scopeText', label: '数据范围' },
  { key: 'actions', label: '操作' },
]

const tableRows = computed(() => rows.value.map((row) => ({
  ...row,
  sourceText: row.sourceText || (row.source === 'DINGTALK_AUTO' ? '钉钉自动' : '手工'),
  statusText: row.statusText || (row.status === 'PENDING_CONFIG' ? '待配置' : row.status === 'DISABLED' ? '停用' : '启用'),
  scopeText: row.scopeText || row.dataScopeText || '未配置',
})))

async function load() {
  const page = await systemAdminApi.rolePage({ pageNo: 1, pageSize: 50 })
  rows.value = page.list || []
}

async function createRole() {
  error.value = ''
  if (!form.value.code || !form.value.name) {
    error.value = '编码、名称必填'
    throw new Error(error.value)
  }
  try {
    await systemAdminApi.roleCreate(form.value)
    toast.success('保存成功')
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败'
    throw err
  }
}

function openPerm(row: Record<string, unknown>) {
  currentId.value = String(row.id)
  checkedMenus.value = []
  writeChecked.value = false
  readChecked.value = false
  previewText.value = ''
  permOpen.value = true
}

function toggleWrite() {
  writeChecked.value = !writeChecked.value
  if (writeChecked.value) readChecked.value = true
}

async function savePerm() {
  await systemAdminApi.roleUpdateMenus(currentId.value, { menuIds: checkedMenus.value })
  await systemAdminApi.roleUpdatePerm(currentId.value, {
    details: [{ code: 'ims:system:dict', r: readChecked.value, w: writeChecked.value, d: false }],
  })
  toast.success('权限已保存')
  await load()
}

async function saveScope() {
  try {
    await systemAdminApi.roleDataScope(currentId.value, { dataScope: scope.value })
    toast.success('数据范围已保存')
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '暂无权限'
  }
}

async function preview() {
  const result = await systemAdminApi.rolePreview(currentId.value, { userId: '1', menuIds: ['param'] })
  const data = result.data as { added?: string[] } | null
  previewText.value = (data?.added || ['参数']).join('、') + ' 新增'
}

async function openMembers(row: Record<string, unknown>) {
  currentId.value = String(row.id)
  const data = await systemAdminApi.roleMembers(currentId.value)
  members.value = data.list || []
  memberOpen.value = true
}

async function removeRole(id: string) {
  try {
    await systemAdminApi.roleDelete(id)
    await load()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '删除失败'
  }
}

async function removeMember(userId: string) {
  await systemAdminApi.roleRemoveMember(currentId.value, userId)
  toast.success('移除后岗位供给不再自动加回')
  memberOpen.value = false
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="page-role">
    <PageHeader title="角色权限" sub-title="角色是权限唯一载体（ADR-IMS-008）" />
    <StatCard :items="stats" />
    <el-button v-if="auth.hasPerm('ims:system:role:create')" data-testid="btn-role-create" type="primary" @click="drawer = true">新建角色</el-button>
    <el-button data-testid="btn-from-position" @click="systemAdminApi.roleFromPosition({ positionCodes: ['POS_A'] }).then(load)">一键从岗位生成角色</el-button>
    <el-button v-if="auth.hasPerm('ims:system:role:export')" data-testid="btn-role-export" @click="systemAdminApi.roleExport()">导出</el-button>
    <p v-if="error" class="error" data-testid="role-error">{{ error }}</p>
    <PlainTable :columns="columns" :data="tableRows">
      <template #cell-actions="{ row }">
        <el-button data-testid="btn-edit-perm" @click="openPerm(row)">编辑权限</el-button>
        <el-button data-testid="btn-scope" @click="currentId = String(row.id); scope = 'DEPT'">数据范围</el-button>
        <el-button data-testid="btn-members" @click="openMembers(row)">成员</el-button>
        <el-button v-if="row.status === 'PENDING_CONFIG'" data-testid="btn-config" @click="openPerm(row)">去配置</el-button>
        <el-button data-testid="btn-role-disable" @click="systemAdminApi.roleUpdateStatus({ id: String(row.id), status: 'DISABLED' }).then(load)">停用</el-button>
        <el-button data-testid="btn-role-delete" @click="removeRole(String(row.id))">删除</el-button>
      </template>
    </PlainTable>
    <div v-if="currentId" class="scope-box">
      <p>本部门不含下级</p>
      <button type="button" data-testid="scope-dept" @click="scope = 'DEPT'; saveScope()">本部门</button>
      <button type="button" data-testid="scope-all" @click="scope = 'ALL'; saveScope()">全部</button>
    </div>
    <FormDrawer v-model:open="drawer" title="新建角色" :submit="createRole">
      <p v-if="error" class="error">{{ error }}</p>
      <label>角色编码<input v-model="form.code" data-testid="field-role-key" /></label>
      <label>名称<input v-model="form.name" data-testid="field-role-name" /></label>
    </FormDrawer>
    <FormDrawer v-model:open="permOpen" title="编辑权限" :submit="savePerm">
      <label><input v-model="checkedMenus" type="checkbox" value="dict" data-testid="perm-dict" /> 字典</label>
      <label><input v-model="checkedMenus" type="checkbox" value="param" data-testid="perm-param" /> 参数</label>
      <label><input type="checkbox" data-testid="perm-w" :checked="writeChecked" @change="toggleWrite" /> W</label>
      <label><input type="checkbox" data-testid="perm-r" :checked="readChecked" disabled /> R</label>
      <el-button data-testid="btn-preview" @click="preview">权限预览</el-button>
      <p data-testid="preview-text">{{ previewText }}</p>
    </FormDrawer>
    <el-dialog v-model="memberOpen" title="成员">
      <p v-for="member in members" :key="String(member.userId)">
        {{ member.nickname }} {{ member.sourceText || member.source }}
        <button type="button" data-testid="btn-remove-member" @click="removeMember(String(member.userId))">移除</button>
      </p>
    </el-dialog>
  </div>
</template>

<style scoped>
.error {
  color: var(--danger, #c45656);
}

label {
  display: block;
  margin: 8px 0;
}
</style>
