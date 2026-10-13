<script setup lang="ts">
/**
 * 用户管理（FP-B2-U）。复用 PageHeader / FormDrawer / ConfirmDialog。
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import ConfirmDialog from '@/components/form/ConfirmDialog.vue'
import { ApiError } from '@/api/request'
import { systemAdminApi, type DeptTreeNode, type UserRow } from '@/api/system-admin'
import { useAuthStore } from '@/stores/auth'
import { useDownloadStore } from '@/stores/download'
import { toast } from '@/utils/toast'
import { PASSWORD_COPY } from '@/utils/password-rules'
import type { TableColumn } from '@/types'

const auth = useAuthStore()
const route = useRoute()
const downloadStore = useDownloadStore()

const tree = ref<DeptTreeNode[]>([])
const users = ref<UserRow[]>([])
const selectedDept = ref('')
const includeChildren = ref(true)
const keyword = ref('')
const status = ref('')
const formOpen = ref(false)
const formError = ref('')
const editing = ref<UserRow | null>(null)
const form = ref({
  username: '',
  nickname: '',
  mobile: '',
  deptId: '',
  mainDeptId: '',
  password: '',
})
const confirmOpen = ref(false)
const confirmMessage = ref('')
const pendingAction = ref<(() => Promise<void>) | null>(null)
const tempPassword = ref('')
const syncMessage = ref('')
const deptError = ref('')
const deptName = ref('')
const deptParent = ref<DeptTreeNode | null>(null)
const deptDialog = ref(false)
const deptMenuId = ref('')
const rowMenuId = ref('')

const can = (code: string) => auth.hasPerm(code)
const columns: TableColumn[] = [
  { key: 'actions', label: '操作' },
  { key: 'id', label: '用户 ID' },
  { key: 'username', label: '用户名' },
  { key: 'nickname', label: '姓名' },
  { key: 'deptName', label: '部门' },
  { key: 'roleText', label: '角色' },
  { key: 'dingtalkBound', label: '钉钉绑定' },
  { key: 'mobile', label: '手机' },
  { key: 'statusText', label: '状态' },
  { key: 'lastLoginTime', label: '最近登录' },
]

const tableRows = computed(() => users.value.map((row) => ({
  ...row,
  roleText: (row.roleNames || []).join('、'),
  statusText: statusLabel(row.status),
})))

function statusLabel(value?: string) {
  if (value === 'FROZEN') return '冻结'
  if (value === 'RESIGNED') return '离职'
  if (value === 'ACTIVE') return '在职'
  return value || '在职'
}

function flatten(nodes: DeptTreeNode[]): DeptTreeNode[] {
  return nodes.flatMap((node) => [node, ...flatten(node.children || [])])
}

const selectedName = computed(() => flatten(tree.value).find((node) => node.id === selectedDept.value)?.name || '')

async function loadTree() {
  tree.value = await systemAdminApi.deptTree()
  const fromQuery = typeof route.query.deptId === 'string' ? route.query.deptId : ''
  if (!selectedDept.value) {
    selectedDept.value = fromQuery || tree.value[0]?.id || ''
  }
}

async function loadUsers() {
  const page = await systemAdminApi.userPage({
    deptId: selectedDept.value,
    includeChildren: includeChildren.value,
    keyword: keyword.value,
    status: status.value,
    pageNo: 1,
    pageSize: 20,
  })
  users.value = page.list || []
}

function selectDept(node: DeptTreeNode) {
  selectedDept.value = node.id
  void loadUsers()
}

function resetForm() {
  formError.value = ''
  form.value = {
    username: '',
    nickname: '',
    mobile: '',
    deptId: selectedDept.value,
    mainDeptId: selectedDept.value,
    password: '',
  }
}

function openCreate() {
  editing.value = null
  resetForm()
  formOpen.value = true
}

function openEdit(row: Record<string, unknown>) {
  editing.value = row as UserRow
  formError.value = ''
  form.value = {
    username: String(row.username || ''),
    nickname: String(row.nickname || ''),
    mobile: String(row.mobile || ''),
    deptId: selectedDept.value,
    mainDeptId: selectedDept.value,
    password: '',
  }
  formOpen.value = true
}

function validateForm() {
  const errors: string[] = []
  if (!editing.value) {
    if (!form.value.username) errors.push('用户名必填')
    if (!form.value.nickname) errors.push('姓名必填')
    if (!form.value.mobile) errors.push('手机号必填')
    if (!form.value.deptId) errors.push('所属部门必填')
    if (!form.value.mainDeptId) errors.push('主部门必填')
    if (!form.value.password) errors.push('初始密码必填')
  }
  const mobileUntouched = form.value.mobile.includes('*')
  if (form.value.mobile && !mobileUntouched && !/^1\d{10}$/.test(form.value.mobile)) errors.push('手机格式错误')
  if (!editing.value && form.value.password && !/^(?=.*[A-Za-z])(?=.*\d)\S{8,32}$/.test(form.value.password)) {
    errors.push(PASSWORD_COPY.rule)
  }
  formError.value = errors.join('；')
  return errors.length === 0
}

async function saveUser() {
  if (!validateForm()) throw new Error(formError.value)
  try {
    if (editing.value) {
      await systemAdminApi.userUpdate({
        id: editing.value.id,
        nickname: form.value.nickname,
        mobile: form.value.mobile,
      })
    } else {
      await systemAdminApi.userCreate({
        username: form.value.username,
        nickname: form.value.nickname,
        mobile: form.value.mobile,
        deptIds: [form.value.deptId],
        mainDeptId: form.value.mainDeptId,
        password: form.value.password,
      })
    }
    toast.success('保存成功')
    await loadUsers()
  } catch (err) {
    formError.value = err instanceof ApiError ? err.message : '保存失败'
    throw err
  }
}

async function deleteDept(node: DeptTreeNode) {
  try {
    await systemAdminApi.deptDelete(node.id)
    await loadTree()
  } catch (err) {
    deptError.value = err instanceof ApiError ? err.message : '删除失败'
  }
}

async function deleteUser(row: UserRow) {
  try {
    await systemAdminApi.userDelete(row.id)
    await loadUsers()
  } catch (err) {
    deptError.value = err instanceof ApiError ? err.message : '删除失败'
  }
}

function ask(message: string, action: () => Promise<void>) {
  confirmMessage.value = message
  pendingAction.value = action
  confirmOpen.value = true
}

async function onConfirm() {
  confirmOpen.value = false
  if (!pendingAction.value) return
  try {
    await pendingAction.value()
    await loadUsers()
  } catch (err) {
    deptError.value = err instanceof ApiError ? err.message : '操作失败'
  }
}

async function resetPassword(row: UserRow) {
  const result = await systemAdminApi.userResetPassword(row.id)
  tempPassword.value = result.data?.tempPassword || ''
}

async function exportUsers() {
  const result = await systemAdminApi.userExport({
    deptId: selectedDept.value,
    includeChildren: includeChildren.value,
  })
  downloadStore.start('用户导出.csv')
  downloadStore.tasks[0].status = 'completed'
  downloadStore.tasks[0].progress = 100
  toast.success(`导出任务 ${result.data?.taskId || ''}`)
}

function openDeptCreate(parent: DeptTreeNode | null) {
  deptParent.value = parent
  deptName.value = ''
  deptDialog.value = true
}

async function saveDept() {
  try {
    await systemAdminApi.deptCreate({
      name: deptName.value,
      parentId: deptParent.value?.id || selectedDept.value,
    })
    toast.success('部门已创建')
    await loadTree()
  } catch (err) {
    deptError.value = err instanceof ApiError ? err.message : '保存失败'
  }
}

async function moveDept(node: DeptTreeNode, parentId: string) {
  try {
    await systemAdminApi.deptMove({ id: node.id, newParentId: parentId })
    await loadTree()
  } catch (err) {
    deptError.value = err instanceof ApiError ? err.message : '移动失败'
  }
}

async function syncOrg() {
  syncMessage.value = ''
  try {
    await systemAdminApi.orgSync()
    syncMessage.value = '同步完成，本地新建的部门不受影响'
    toast.success(syncMessage.value)
    await loadTree()
    await loadUsers()
  } catch (err) {
    syncMessage.value = err instanceof ApiError ? err.message : '同步失败'
  }
}

onMounted(async () => {
  await loadTree()
  await loadUsers()
})
</script>

<template>
  <div data-testid="page-user">
    <PageHeader title="用户" sub-title="系统管理 / 用户管理" />
    <div class="toolbar">
      <el-button v-if="can('ims:system:user:export')" data-testid="btn-export" @click="exportUsers">导出</el-button>
      <el-button v-if="can('ims:system:user:create')" type="primary" data-testid="btn-create" @click="openCreate">新建用户</el-button>
      <el-button v-if="can('ims:system:org-sync:run')" data-testid="btn-sync" @click="syncOrg">同步钉钉组织</el-button>
    </div>
    <p v-if="syncMessage" data-testid="sync-message">{{ syncMessage }}</p>
    <p v-if="deptError" class="error" data-testid="dept-error">{{ deptError }}</p>
    <div class="split">
      <aside class="tree" data-testid="dept-tree">
        <div v-for="node in flatten(tree)" :key="node.id" class="dept-row">
          <button type="button" :data-testid="`dept-${node.name}`" @click="selectDept(node)">
            {{ node.name }}（{{ node.memberCount || 0 }}）
          </button>
          <template v-if="can('ims:system:dept:update') && node.name !== '待分配'">
            <button type="button" :data-testid="`dept-more-${node.name}`" @click="deptMenuId = deptMenuId === node.id ? '' : node.id">更多</button>
            <template v-if="deptMenuId === node.id">
              <button v-if="can('ims:system:dept:create')" type="button" :data-testid="`dept-add-${node.name}`" @click="openDeptCreate(node)">新增下级</button>
              <button type="button" :data-testid="`dept-move-${node.name}`" @click="moveDept(node, tree[0]?.id || node.id)">移动</button>
              <button v-if="can('ims:system:dept:delete')" type="button" :data-testid="`dept-del-${node.name}`" @click="deleteDept(node)">删除</button>
            </template>
          </template>
          <span v-else-if="node.name === '待分配'" data-testid="dept-pending-locked">待分配不可改</span>
        </div>
      </aside>
      <section>
        <div class="filters">
          <input v-model="keyword" data-testid="user-keyword" placeholder="用户名/姓名/手机" />
          <select v-model="status" data-testid="user-status">
            <option value="">全部</option>
            <option value="ACTIVE">在职</option>
            <option value="FROZEN">冻结</option>
            <option value="RESIGNED">离职</option>
          </select>
          <label>
            含下级
            <input v-model="includeChildren" data-testid="include-children" type="checkbox" @change="loadUsers" />
          </label>
          <el-button data-testid="btn-query" @click="loadUsers">查询</el-button>
        </div>
        <p data-testid="selected-dept">当前部门：{{ selectedName }}</p>
        <PlainTable :columns="columns" :data="tableRows">
          <template #cell-actions="{ row }">
            <el-button v-if="can('ims:system:user:update') && row.status !== 'RESIGNED'" data-testid="btn-edit" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 'RESIGNED'" data-testid="btn-view">查看</el-button>
            <template v-if="can('ims:system:user:update') && row.status !== 'RESIGNED'">
              <button type="button" data-testid="row-more" @click="rowMenuId = rowMenuId === String(row.id) ? '' : String(row.id)">更多</button>
              <template v-if="rowMenuId === String(row.id)">
                <button type="button" data-testid="act-freeze" @click="ask('冻结后该用户所有设备立即下线且不能登录', () => systemAdminApi.userUpdateStatus({ id: String(row.id), status: 'FROZEN' }))">冻结</button>
                <button type="button" data-testid="act-unfreeze" @click="systemAdminApi.userUpdateStatus({ id: String(row.id), status: 'ACTIVE' }).then(loadUsers)">解冻</button>
                <button v-if="can('ims:system:user:reset-pwd')" type="button" data-testid="act-reset" @click="resetPassword(row)">重置密码</button>
                <button v-if="row.locked && can('ims:system:user:unlock')" type="button" data-testid="act-unlock" @click="systemAdminApi.userUnlock(String(row.id)).then(loadUsers)">解锁</button>
                <button v-if="can('ims:system:user:kick')" type="button" data-testid="act-kick" @click="systemAdminApi.userKick(String(row.id)).then(() => toast.success('已强制下线'))">强制下线</button>
                <button type="button" data-testid="act-resign" @click="ask('已知晓离职不可恢复', () => systemAdminApi.userResign(String(row.id)))">办理离职</button>
                <button v-if="can('ims:system:user:delete')" type="button" data-testid="act-delete" @click="deleteUser(row)">删除</button>
              </template>
            </template>
          </template>
        </PlainTable>
      </section>
    </div>

    <FormDrawer v-model:open="formOpen" :title="editing ? '编辑用户' : '新建用户'" size="M" :submit="saveUser">
      <p v-if="formError" class="error" data-testid="form-error">{{ formError }}</p>
      <label>用户 ID<input data-testid="field-id" :value="editing?.id || '保存后生成'" readonly /></label>
      <label>用户名<input v-model="form.username" data-testid="field-username" :readonly="!!editing" /></label>
      <label>姓名<input v-model="form.nickname" data-testid="field-nickname" /></label>
      <label>手机号<input v-model="form.mobile" data-testid="field-mobile" /></label>
      <label>所属部门<input v-model="form.deptId" data-testid="field-dept" /></label>
      <label>主部门<input v-model="form.mainDeptId" data-testid="field-main-dept" /></label>
      <label v-if="!editing">初始密码<input v-model="form.password" data-testid="field-password" /></label>
    </FormDrawer>

    <div v-if="deptDialog" class="dept-form">
      <input v-model="deptName" data-testid="field-dept-name" placeholder="部门名称" />
      <el-button data-testid="btn-dept-save" @click="saveDept">保存部门</el-button>
    </div>

    <el-dialog :model-value="!!tempPassword" title="临时密码" @close="tempPassword = ''">
      <p data-testid="temp-password">{{ tempPassword }}</p>
    </el-dialog>

    <ConfirmDialog v-model:open="confirmOpen" :message="confirmMessage" @confirm="onConfirm" />
  </div>
</template>

<style scoped>
.toolbar,
.filters,
.dept-row,
.dept-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.split {
  display: flex;
  gap: 16px;
}

.tree {
  width: 240px;
}

.error {
  color: var(--danger, #c45656);
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}
</style>
