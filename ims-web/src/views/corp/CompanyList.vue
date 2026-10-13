<script setup lang="ts">
/**
 * 公司管理。登录加权限，不按数据范围分列表。版本 v1.0 · 2026-10-13
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCompany,
  expandCompany,
  exportCompanies,
  getCompany,
  pageCompanies,
  updateCompanyStatus,
  type CompanyRow,
} from '@/api/resource'
import { ApiError } from '@/api/request'

const rows = ref<CompanyRow[]>([])
const total = ref(0)
const query = reactive({ name: '', creditCode: '', status: '' })
const formOpen = ref(false)
const detailOpen = ref(false)
const expandOpen = ref(false)
const current = ref<CompanyRow | null>(null)
const form = reactive({ name: '', creditCode: '', mpCapacity: 0 })
const expandForm = reactive({ toCapacity: 0, reason: '' })
const nameError = ref('')
const exportText = ref('')

async function load() {
  const page = await pageCompanies({ name: query.name, status: query.status })
  let list = page.list || []
  if (query.creditCode) list = list.filter((item) => (item.creditCode || '').includes(query.creditCode))
  rows.value = list
  total.value = query.creditCode ? list.length : page.total
}

function reset() {
  query.name = ''
  query.creditCode = ''
  query.status = ''
  load()
}

function openCreate() {
  form.name = ''
  form.creditCode = ''
  form.mpCapacity = 0
  nameError.value = ''
  formOpen.value = true
}

async function save() {
  nameError.value = ''
  if (!form.name.trim()) {
    nameError.value = '必填项，请填写'
    return
  }
  try {
    await createCompany({
      name: form.name.trim(),
      creditCode: form.creditCode,
      mpCapacity: form.mpCapacity,
    })
    formOpen.value = false
    await load()
  } catch (err) {
    // 1001 全局不弹，由页面带出后端原文（名称重复、信用代码）。
    if (err instanceof ApiError) ElMessage.error(err.message)
  }
}

async function openDetail(row: CompanyRow) {
  current.value = await getCompany(row.id)
  detailOpen.value = true
}

async function submitExpand() {
  if (!current.value) return
  try {
    current.value = await expandCompany(current.value.id, Number(expandForm.toCapacity), expandForm.reason)
    expandOpen.value = false
    await load()
  } catch {
    // 1222 等业务码由请求层弹出一次，这里不再叠一条。
  }
}

async function toggleStatus(row: CompanyRow) {
  const next = row.statusCode === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  if (next === 'DISABLED') {
    await ElMessageBox.confirm('已关联账号不受影响', '停用公司')
  }
  await updateCompanyStatus(row.id, next)
  await load()
}

async function doExport() {
  await exportCompanies({ name: query.name, status: query.status })
  exportText.value = `已提交导出，共 ${rows.value.length} 行，身份证已脱敏`
  ElMessage.success(exportText.value)
}

onMounted(load)
</script>

<template>
  <div class="company-page" data-testid="company-page">
      <header class="page-head">
        <h1>公司管理</h1>
        <div>
          <el-button v-perm="'ims:corp:company:export'" @click="doExport">导出</el-button>
          <el-button v-perm="'ims:corp:company:create'" type="primary" @click="openCreate">新建公司</el-button>
        </div>
      </header>
      <div class="filters">
        <el-input v-model="query.name" placeholder="名称" />
        <el-input v-model="query.creditCode" placeholder="信用代码" />
        <el-select v-model="query.status" placeholder="状态" clearable>
          <el-option label="启用" value="ENABLED" />
          <el-option label="停用" value="DISABLED" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
      <p v-if="exportText" data-testid="export-preview">{{ exportText }}</p>
      <el-table :data="rows">
        <el-table-column prop="id" label="公司 ID" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="creditCode" label="信用代码" />
        <el-table-column label="公众号容量">
          <template #default="{ row }">
            <span>{{ row.mpRegistered }} / {{ row.mpCapacity }}</span>
            <el-tag v-if="row.capacityTight" type="warning">容量紧张</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button link @click="openDetail(row)">详情</el-button>
            <el-button v-perm="'ims:corp:company:update'" link @click="toggleStatus(row)">
              {{ row.statusCode === 'ENABLED' ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-drawer v-model="formOpen" title="新建公司">
        <el-form label-position="top">
          <el-form-item label="公司名称" :error="nameError">
            <el-input v-model="form.name" placeholder="公司名称" />
          </el-form-item>
          <el-form-item label="信用代码">
            <el-input v-model="form.creditCode" placeholder="信用代码" />
          </el-form-item>
          <el-form-item label="公众号容量">
            <el-input v-model.number="form.mpCapacity" placeholder="容量" />
          </el-form-item>
        </el-form>
        <el-button type="primary" @click="save">保存</el-button>
      </el-drawer>

      <el-drawer v-model="detailOpen" title="公司详情">
        <template v-if="current">
          <p>总量 {{ current.mpCapacity }} / 已注册 {{ current.mpRegistered }} / 剩余 {{ current.mpCapacity - current.mpRegistered }}</p>
          <p v-if="!(current.expansions && current.expansions.length)">关联账号空状态</p>
          <ul>
            <li v-for="item in current.expansions || []" :key="item.id">
              原 {{ item.fromCapacity }} → 新 {{ item.toCapacity }} {{ item.operatorName || '' }} {{ item.reason }}
            </li>
          </ul>
          <el-button v-perm="'ims:corp:company:expand'" @click="expandOpen = true">扩容</el-button>
        </template>
      </el-drawer>

      <el-dialog v-model="expandOpen" title="扩容">
        <el-input v-model.number="expandForm.toCapacity" placeholder="新容量" />
        <el-input v-model="expandForm.reason" placeholder="扩容原因" />
        <el-button type="primary" @click="submitExpand">确认扩容</el-button>
      </el-dialog>
  </div>
</template>

<style scoped>
.page-head,
.filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.page-head {
  justify-content: space-between;
}
</style>
