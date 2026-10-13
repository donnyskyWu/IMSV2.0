<script setup lang="ts">
/**
 * 实名人与中介人。证件号、手机号只展示脱敏值。版本 v1.0 · 2026-10-13
 */
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ApiError } from '@/api/request'
import {
  createIntermediary,
  createRealname,
  deleteRealname,
  exportRealnames,
  getRealname,
  pageRealnames,
  updateRealnameStatus,
  type RealnameRow,
} from '@/api/resource'

const router = useRouter()
const rows = ref<RealnameRow[]>([])
const query = reactive({ name: '', idCard: '', status: '' })
const formOpen = ref(false)
const detailOpen = ref(false)
const current = ref<RealnameRow | null>(null)
const errors = ref<string[]>([])
const exportText = ref('')
const form = reactive({ name: '', idType: '', idCard: '', phone: '' })
const person = reactive({ name: '', commissionRate: '' })

async function load() {
  const page = await pageRealnames({ name: query.name, idCard: query.idCard, status: query.status })
  rows.value = page.list || []
}

function openCreate() {
  form.name = ''
  form.idType = ''
  form.idCard = ''
  form.phone = ''
  errors.value = []
  formOpen.value = true
}

async function save() {
  errors.value = []
  if (!form.name.trim()) errors.value.push('姓名必填')
  if (!form.idType) errors.value.push('证件类型必填')
  if (!form.idCard.trim()) errors.value.push('证件号必填')
  if (errors.value.length) {
    errors.value.push('必填项，请填写')
    return
  }
  try {
    await createRealname({ ...form })
    formOpen.value = false
    await load()
  } catch (err) {
    // 1001 全局不弹。身份证、证件号重复都用后端原文。
    if (err instanceof ApiError) ElMessage.error(err.message)
  }
}

async function openDetail(row: RealnameRow) {
  current.value = await getRealname(row.id)
  detailOpen.value = true
}

async function addPerson() {
  if (!current.value) return
  await createIntermediary(current.value.id, { name: person.name, commissionRate: person.commissionRate })
  current.value = await getRealname(current.value.id)
  person.name = ''
  person.commissionRate = ''
  await load()
}

async function setStatus(row: RealnameRow, status: string) {
  await updateRealnameStatus(row.id, status)
  await load()
}

async function remove(row: RealnameRow) {
  try {
    await deleteRealname(row.id)
    await load()
  } catch (err) {
    if (err instanceof ApiError) {
      const refs = (err.data as { refs?: Array<{ type: string; count: number }> } | null)?.refs || []
      const text = refs.map((item) => `${item.type}:${item.count}`).join(' ')
      // 删除接口关掉了全局提示，这里把引用次数拼进同一条。
      ElMessage.error(`${err.message} ${text}`.trim())
    }
  }
}

async function doExport() {
  await exportRealnames({ status: query.status })
  exportText.value = `已提交导出，共 ${rows.value.length} 行，证件号与手机号已脱敏，无佣金列`
  ElMessage.success(exportText.value)
}

function openCert(id: string) {
  router.push({ path: '/ims/corp/resource/certificate', query: { holder: id } })
}

onMounted(load)
</script>

<template>
  <div data-testid="realname-page">
      <header class="page-head">
        <h1>实名人管理</h1>
        <div>
          <el-button v-perm="'ims:corp:realname:export'" @click="doExport">导出</el-button>
          <el-button v-perm="'ims:corp:realname:create'" type="primary" @click="openCreate">新增实名人</el-button>
        </div>
      </header>
      <div class="filters">
        <el-input v-model="query.name" placeholder="姓名" />
        <el-input v-model="query.idCard" placeholder="证件号" />
        <el-select v-model="query.status" placeholder="状态" clearable>
          <el-option label="在职" value="ON_JOB" />
          <el-option label="离职" value="LEFT" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <p v-if="exportText" data-testid="rn-export">{{ exportText }}</p>
      <el-table :data="rows">
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="idCard" label="证件号" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column label="中介人">
          <template #default="{ row }">{{ row.intermediaryText || '' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button link @click="openDetail(row)">详情</el-button>
            <el-button v-perm="'ims:corp:realname:update'" link @click="setStatus(row, row.statusCode === 'ON_JOB' ? 'LEFT' : 'ON_JOB')">
              {{ row.statusCode === 'ON_JOB' ? '离职' : '恢复在职' }}
            </el-button>
            <el-button v-perm="'ims:corp:realname:delete'" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-drawer v-model="formOpen" title="新增实名人">
        <p v-for="item in errors" :key="item" class="err">{{ item }}</p>
        <el-input v-model="form.name" placeholder="姓名" />
        <el-select v-model="form.idType" placeholder="证件类型">
          <el-option label="居民身份证" value="ID_CARD" />
          <el-option label="护照" value="PASSPORT" />
        </el-select>
        <el-input v-model="form.idCard" placeholder="证件号" />
        <el-input v-model="form.phone" placeholder="手机号" />
        <el-button type="primary" @click="save">保存</el-button>
      </el-drawer>

      <el-drawer v-model="detailOpen" title="实名人详情">
        <template v-if="current">
          <p>{{ current.name }} {{ current.idCard }} {{ current.phone }}</p>
          <p v-if="current.intermediaries?.some((item) => !item.commissionRate)">佣金比例 ****</p>
          <ul>
            <li v-for="item in current.intermediaries || []" :key="item.id">
              {{ item.name }}
              <span v-if="item.commissionRate">佣金 {{ item.commissionRate }}</span>
            </li>
          </ul>
          <p>证件索引</p>
          <el-button v-for="cert in current.certs || []" :key="cert.id" link @click="openCert(current.id)">
            {{ cert.name }}
          </el-button>
          <p>关联手机卡</p>
          <span v-for="sim in current.sims || []" :key="sim.id">{{ sim.name }}</span>
          <div v-perm="'ims:corp:realname:update'">
            <el-input v-model="person.name" placeholder="中介人姓名" />
            <el-input v-model="person.commissionRate" placeholder="佣金" />
            <el-button @click="addPerson">添加中介人</el-button>
          </div>
        </template>
      </el-drawer>
  </div>
</template>

<style scoped>
.page-head,
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.page-head {
  justify-content: space-between;
}

.err {
  color: var(--el-color-danger);
}
</style>
