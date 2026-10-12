<script setup lang="ts">
/**
 * 列表演示页 (FP-P-04)
 * 依据: UI-L01, 00-工作包 §2.3 U3
 * 包含:
 * - UI-L01 标准列表: 查询、排序、分页、状态标签、金额、脱敏
 * - 一条首列超长名称的记录 (VC-M-07)
 */
import { ref, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import ConfirmDialog from '@/components/form/ConfirmDialog.vue'
import { fmtMoney } from '@/utils/format'

// 模拟订单数据 (35条)
// §2.3 U3: 提供一条首列超长名称的记录
const mockOrders = Array.from({ length: 35 }, (_, i) => ({
  id: String(i + 1),
  // VC-M-07: 首列超长名称 (第一条记录)
  name: i === 0
    ? '这是一个非常长的订单名称用于验证移动端首列宽度限制为120像素并且超出部分显示省略号点击后tooltip显示全文的功能测试'
    : `示例订单 ${String(i + 1).padStart(3, '0')}`,
  orderNo: `ORD${String(2026100001 + i)}`,
  amount: Math.round((Math.random() * 10000 - 2000) * 100) / 100, // 包含负数
  status: ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'][i % 5],
  idCard: i % 3 === 0 ? '110***********1234' : null,
  cost: i % 4 === 0 ? '***' : String(Math.round(Math.random() * 1000)),
  createTime: `2026-10-${String((i % 28) + 1).padStart(2, '0')} ${String((i % 12) + 8).padStart(2, '0')}:${String(i % 60).padStart(2, '0')}`,
}))

// 分页状态
const pageNo = ref(1)
const pageSize = ref(10)

// 查询条件
const searchForm = ref({
  name: '',
  status: '',
  dateRange: [],
})

// 排序
const sortField = ref('')
const sortOrder = ref<'asc' | 'desc' | ''>('')

// 计算当前页数据
const filteredData = computed(() => {
  let data = [...mockOrders]

  // 筛选
  if (searchForm.value.name) {
    data = data.filter(d => d.name.includes(searchForm.value.name))
  }
  if (searchForm.value.status) {
    data = data.filter(d => d.status === searchForm.value.status)
  }

  // 排序
  if (sortField.value && sortOrder.value) {
    data.sort((a, b) => {
      const aVal = a[sortField.value as keyof typeof a]
      const bVal = b[sortField.value as keyof typeof b]
      const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      return sortOrder.value === 'desc' ? -cmp : cmp
    })
  }

  return data
})

const total = computed(() => filteredData.value.length)

const tableData = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

// 查询
function handleSearch() {
  pageNo.value = 1
}

// 重置
function handleReset() {
  searchForm.value = { name: '', status: '', dateRange: [] }
  pageNo.value = 1
}

// 排序变化
function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  sortField.value = prop || ''
  sortOrder.value = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : ''
}

// 新建/编辑抽屉
const drawerVisible = ref(false)
const drawerTitle = ref('新建')
const formModel = ref({ name: '', amount: 0 })

function handleCreate() {
  drawerTitle.value = '新建'
  formModel.value = { name: '', amount: 0 }
  drawerVisible.value = true
}

function handleEdit(row: typeof mockOrders[0]) {
  drawerTitle.value = '编辑'
  formModel.value = { name: row.name, amount: row.amount }
  drawerVisible.value = true
}

async function handleSubmit() {
  console.log('Submit:', formModel.value)
  // 模拟保存
  return new Promise(resolve => setTimeout(resolve, 500))
}

function handleSaved() {
  drawerVisible.value = false
  pageNo.value = 1 // 新建后回到第1页
}

// 删除
const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)

async function handleDelete(row: typeof mockOrders[0]) {
  try {
    await confirmDialogRef.value?.confirm({
      title: '确定删除',
      message: `确定删除订单「${row.name}」？`,
      danger: true,
    })
    console.log('Delete:', row.id)
    // 模拟删除后刷新
  } catch {
    // 取消
  }
}

// 导入/导出
function handleImport() {
  console.log('Import')
}

function handleExport() {
  console.log('Export')
}
</script>

<template>
  <AppLayout>
    <div class="list-demo">
      <PageHeader title="列表演示" sub-title="FP-P-04 / UI-L01">
        <template #actions>
          <el-button type="primary" @click="handleCreate">新建</el-button>
          <el-button @click="handleImport">导入</el-button>
          <el-button @click="handleExport">导出</el-button>
        </template>
        <template #primary-action>
          <el-button type="primary" @click="handleCreate">新建</el-button>
        </template>
      </PageHeader>

      <!-- 查询栏 -->
      <div class="query-bar">
        <el-form :model="searchForm" inline @submit.prevent="handleSearch">
          <el-form-item label="名称">
            <el-input
              v-model="searchForm.name"
              placeholder="请输入名称"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="searchForm.status"
              placeholder="全部"
              clearable
              style="width: 120px"
            >
              <el-option label="草稿" value="DRAFT" />
              <el-option label="待审批" value="PENDING" />
              <el-option label="已通过" value="APPROVED" />
              <el-option label="已驳回" value="REJECTED" />
              <el-option label="已取消" value="CANCELLED" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 数据表格 -->
      <div class="table-wrap">
        <el-table
          :data="tableData"
          style="width: 100%"
          @sort-change="handleSortChange"
        >
          <!-- 名称列 (VC-M-07: 首列宽度 ≤120px，超长省略号，点击tooltip显示全文) -->
          <el-table-column
            prop="name"
            label="名称"
            min-width="120"
            fixed="left"
            show-overflow-tooltip
          />
          <el-table-column prop="orderNo" label="订单号" width="140">
            <template #default="{ row }">
              <span class="mono">{{ row.orderNo }}</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="amount"
            label="金额"
            width="120"
            align="right"
            sortable="custom"
          >
            <template #default="{ row }">
              <span :class="{ neg: row.amount < 0 }">
                {{ fmtMoney(row.amount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <StatusTag dict-type="demo_order_status" :value="row.status" />
            </template>
          </el-table-column>
          <el-table-column prop="idCard" label="证件号" width="150">
            <template #default="{ row }">
              <span v-if="row.idCard" class="mono">{{ row.idCard }}</span>
              <span v-else class="empty-placeholder">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="cost" label="成本" width="100">
            <template #default="{ row }">
              <el-tooltip
                v-if="row.cost === '***'"
                content="无查看权限"
                placement="top"
              >
                <span class="masked">***</span>
              </el-tooltip>
              <span v-else>{{ row.cost }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" width="160" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="handleEdit(row)">
                编辑
              </el-button>
              <el-button text type="primary" size="small">
                查看
              </el-button>
              <el-dropdown trigger="click">
                <el-button text type="primary" size="small">更多</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>复制</el-dropdown-item>
                    <el-dropdown-item divided @click="handleDelete(row)">
                      <span class="danger-text">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>

        <!-- 空态 -->
        <EmptyState v-if="tableData.length === 0" type="empty" />
      </div>

      <!-- 分页 -->
      <Pagination
        v-model:page-no="pageNo"
        v-model:page-size="pageSize"
        :total="total"
      />

      <!-- 新建/编辑抽屉 -->
      <FormDrawer
        v-model:open="drawerVisible"
        :title="drawerTitle"
        size="M"
        :submit="handleSubmit"
        @saved="handleSaved"
      >
        <el-form :model="formModel" label-width="80px">
          <el-form-item label="名称" required>
            <el-input v-model="formModel.name" placeholder="请输入名称" />
          </el-form-item>
          <el-form-item label="金额" required>
            <el-input-number v-model="formModel.amount" :precision="2" />
          </el-form-item>
        </el-form>
      </FormDrawer>

      <!-- 确认对话框 -->
      <ConfirmDialog ref="confirmDialogRef" />
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.list-demo {
  width: 100%;
}

.query-bar {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }

  :deep(.el-input) {
    width: 180px;
  }
}

.table-wrap {
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  overflow: hidden;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
}

.neg {
  color: var(--red);
}

.masked {
  color: var(--text2);
  cursor: help;
}

.empty-placeholder {
  color: var(--text2);
}

.danger-text {
  color: var(--red);
}
</style>
