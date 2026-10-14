<script setup lang="ts">
/**
 * 手机卡。号码脱敏，编辑不改号码。版本 v1.0 · 2026-10-13
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import RealNameSelect from '@/components/selector/RealNameSelect.vue'
import { ApiError } from '@/api/request'
import {
  createSimCard,
  deleteSimCard,
  exportSimCards,
  getSimCard,
  pageSimCards,
  updateSimCard,
  type SimRow,
} from '@/api/resource'

const rows = ref<SimRow[]>([])
const query = reactive({ phone: '', realname: '', operator: '' })
const formOpen = ref(false)
const detailOpen = ref(false)
const editing = ref(false)
const current = ref<SimRow | null>(null)
const errors = ref<string[]>([])
const exportText = ref('')
const form = reactive({ phone: '', operator: '', realnameId: '', monthlyRent: '', iccid: '' })

async function load() {
  const page = await pageSimCards({ operator: query.operator, phone: query.phone })
  let list = page.list || []
  if (query.realname.trim()) {
    list = list.filter((item) => (item.realnameName || '').includes(query.realname.trim()))
  }
  rows.value = list
}

function reset() {
  query.phone = ''
  query.realname = ''
  query.operator = ''
  load()
}

function openCreate() {
  editing.value = false
  current.value = null
  form.phone = ''
  form.operator = ''
  form.realnameId = ''
  form.monthlyRent = ''
  form.iccid = ''
  errors.value = []
  formOpen.value = true
}

async function save() {
  errors.value = []
  if (!editing.value) {
    if (!form.phone.trim()) errors.value.push('号码必填')
    if (!form.operator) errors.value.push('运营商必填')
    if (!form.realnameId) errors.value.push('实名人必填')
    if (errors.value.length) return
  }
  try {
    if (editing.value && current.value) {
      await updateSimCard(current.value.id, {
        operator: form.operator,
        monthlyRent: form.monthlyRent,
        iccid: form.iccid,
      })
    } else {
      await createSimCard({ ...form })
    }
    formOpen.value = false
    await load()
  } catch (err) {
    // 1001 全局不弹（号码、ICCID 重复）。1501 已由请求层弹出。
    if (err instanceof ApiError && err.code === 1001) ElMessage.error(err.message)
  }
}

async function openDetail(row: SimRow) {
  current.value = await getSimCard(row.id)
  detailOpen.value = true
}

function openEdit(row: SimRow) {
  editing.value = true
  current.value = row
  form.phone = row.phone
  form.operator = row.operator
  form.realnameId = row.realnameId
  form.monthlyRent = row.monthlyRent
  form.iccid = ''
  formOpen.value = true
}

async function remove(row: SimRow) {
  await deleteSimCard(row.id)
  await load()
}

async function doExport() {
  await exportSimCards()
  exportText.value = `已提交导出，共 ${rows.value.length} 行，号码与 ICCID 已脱敏`
  ElMessage.success(exportText.value)
}

onMounted(load)
</script>

<template>
  <div data-testid="sim-page">
      <header class="page-head">
        <h1>手机卡管理</h1>
        <div>
          <el-button v-perm="'ims:corp:sim:export'" @click="doExport">导出</el-button>
          <el-button v-perm="'ims:corp:sim:create'" type="primary" @click="openCreate">新增手机卡</el-button>
        </div>
      </header>
      <div class="filters">
        <el-input v-model="query.phone" placeholder="号码" />
        <el-input v-model="query.realname" placeholder="实名人" />
        <el-select v-model="query.operator" placeholder="运营商" clearable>
          <el-option label="移动" value="CMCC" />
          <el-option label="联通" value="CUCC" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
      <p v-if="exportText" data-testid="sm-export">{{ exportText }}</p>
      <div class="table-scroll">
      <el-table :data="rows">
        <el-table-column prop="id" label="卡 ID" />
        <el-table-column prop="phone" label="号码" />
        <el-table-column prop="operatorLabel" label="运营商" />
        <el-table-column prop="realnameName" label="实名人" />
        <el-table-column label="月租">
          <template #default="{ row }">¥{{ row.monthlyRent }}</template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button link @click="openDetail(row)">详情</el-button>
            <el-button v-perm="'ims:corp:sim:update'" link @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'ims:corp:sim:delete'" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      </div>

      <el-drawer v-model="formOpen" :title="editing ? '编辑手机卡' : '新增手机卡'">
        <p v-for="item in errors" :key="item">{{ item }}</p>
        <el-input v-model="form.phone" placeholder="号码" :disabled="editing" />
        <el-select v-model="form.operator" placeholder="运营商">
          <el-option label="移动" value="CMCC" />
          <el-option label="联通" value="CUCC" />
        </el-select>
        <RealNameSelect v-if="!editing" v-model="form.realnameId" />
        <el-input v-model="form.monthlyRent" placeholder="月租" />
        <el-input v-model="form.iccid" placeholder="ICCID" />
        <el-button type="primary" @click="save">保存</el-button>
      </el-drawer>

      <el-drawer v-model="detailOpen" title="手机卡详情">
        <template v-if="current">
          <p>实名人 {{ current.realnameName || current.realnameId }}</p>
          <p>月租 ¥{{ current.monthlyRent }}</p>
          <p>号码 {{ current.phone }}</p>
          <p v-if="!(current.accounts && current.accounts.length)">关联平台账号空状态</p>
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

.table-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
}
</style>
