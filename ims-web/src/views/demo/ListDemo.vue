<script setup lang="ts">
/**
 * 列表演示页 (FP-P-04)
 * 依据: UI-L01, 00-工作包 §2.3 U3
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import Chip from '@/components/list/Chip.vue'
import { fmtMoney } from '@/utils/format'
import { toast } from '@/utils/toast'
import { useDictStore } from '@/stores/dict'
import { useResponsive } from '@/utils/responsive'
import type { EmptyType } from '@/types'

interface Order {
  id: string
  name: string
  orderNo: string
  amount: number
  status: string
  idCard: string | null
  cost: string
  createTime: string
  referenced?: boolean
}

const dictStore = useDictStore()
const { isMobile } = useResponsive()

const orders = ref<Order[]>(
  Array.from({ length: 35 }, (_, i) => ({
    id: String(i + 1),
    name: i === 0
      ? '这是一个非常长的订单名称用于验证移动端首列宽度限制为120像素并且超出部分显示省略号点击后tooltip显示全文的功能测试'
      : `示例订单 ${String(i + 1).padStart(3, '0')}`,
    orderNo: `ORD${String(2026100001 + i)}`,
    amount: Math.round((i * 137 - 2000) * 100) / 100,
    status: ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'][i % 5],
    idCard: i % 3 === 0 ? '110***********1234' : null,
    cost: i % 4 === 0 ? '***' : String(100 + i),
    createTime: `2026-10-${String((i % 28) + 1).padStart(2, '0')} 10:00`,
    referenced: i === 2,
  })),
)

const pageNo = ref(1)
const pageSize = ref(10)
const showMore = ref(false)
const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')
const retried = ref(0)
const selected = ref<Order[]>([])
const saveCount = ref(0)

const searchForm = ref({
  name: '',
  status: '',
  orderNo: '',
  amount: '',
  idCard: '',
  created: '',
})

const sortField = ref('')
const sortOrder = ref<'asc' | 'desc' | ''>('')

const STATE_KEY = 'ims_list_state'

const filteredData = computed(() => {
  let data = [...orders.value]
  const q = searchForm.value
  if (q.name) data = data.filter((d) => d.name.includes(q.name))
  if (q.status) data = data.filter((d) => d.status === q.status)
  if (q.orderNo) data = data.filter((d) => d.orderNo.includes(q.orderNo))
  if (sortField.value && sortOrder.value) {
    data.sort((a, b) => {
      const aVal = a[sortField.value as keyof Order]
      const bVal = b[sortField.value as keyof Order]
      const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      return sortOrder.value === 'desc' ? -cmp : cmp
    })
  }
  return data
})

const total = computed(() => (emptyMode.value ? 0 : filteredData.value.length))

const tableData = computed(() => {
  if (emptyMode.value) return []
  const start = (pageNo.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

const chips = computed(() => {
  const list: { key: keyof typeof searchForm.value; label: string }[] = []
  if (searchForm.value.name) list.push({ key: 'name', label: `名称: ${searchForm.value.name}` })
  if (searchForm.value.status) list.push({ key: 'status', label: `状态: ${searchForm.value.status}` })
  if (searchForm.value.orderNo) list.push({ key: 'orderNo', label: `订单号: ${searchForm.value.orderNo}` })
  return list
})

function persist() {
  sessionStorage.setItem(STATE_KEY, JSON.stringify({
    ...searchForm.value,
    pageNo: pageNo.value,
  }))
}

function handleSearch() {
  pageNo.value = 1
  persist()
}

function handleReset() {
  searchForm.value = { name: '', status: '', orderNo: '', amount: '', idCard: '', created: '' }
  pageNo.value = 1
  emptyMode.value = ''
  persist()
}

function closeChip(key: keyof typeof searchForm.value) {
  searchForm.value[key] = ''
  handleSearch()
}

function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  sortField.value = prop || ''
  sortOrder.value = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : ''
}

const drawerVisible = ref(false)
const drawerTitle = ref('新建')
const formModel = ref({ name: '', amount: 0 })
const amountText = ref('')
const amountError = ref('')
const detailOpen = ref(false)
const detailTab = ref('base')
const detailRow = ref<Order | null>(null)

function checkAmount() {
  amountError.value = /^\d+\.\d{3,}$/.test(amountText.value.trim()) ? '金额最多 2 位小数' : ''
}

function handleView(row: Order) {
  detailRow.value = row
  detailTab.value = 'base'
  detailOpen.value = true
}

function handleCreate() {
  drawerTitle.value = '新建'
  formModel.value = { name: '', amount: 0 }
  drawerVisible.value = true
}

async function handleSubmit() {
  await new Promise((resolve) => setTimeout(resolve, 400))
  saveCount.value += 1
  const name = formModel.value.name || `新订单 ${saveCount.value}`
  orders.value.unshift({
    id: `new-${saveCount.value}`,
    name,
    orderNo: `ORDNEW${saveCount.value}`,
    amount: formModel.value.amount,
    status: 'DRAFT',
    idCard: null,
    cost: '0',
    createTime: '2026-10-12 12:00',
  })
  toast.success('保存成功')
  pageNo.value = 1
}

const confirmOpen = ref(false)
const confirmError = ref('')
const pendingDelete = ref<Order | null>(null)

function handleDelete(row: Order) {
  pendingDelete.value = row
  confirmError.value = ''
  confirmOpen.value = true
}

function confirmDelete() {
  const row = pendingDelete.value
  if (!row) return
  if (row.referenced) {
    confirmError.value = '关联的实体已被其他记录引用'
    return
  }
  orders.value = orders.value.filter((item) => item.id !== row.id)
  confirmOpen.value = false
  toast.success('已删除')
}

function refreshDict() {
  const current = [
    { value: 'DRAFT', label: '草稿', colorType: 'neutral' as const },
    { value: 'PENDING', label: '测试名', colorType: 'purple' as const },
    { value: 'APPROVED', label: '已通过', colorType: 'success' as const },
    { value: 'REJECTED', label: '已退回', colorType: 'danger' as const },
    { value: 'CANCELLED', label: '已取消', colorType: 'neutral' as const },
  ]
  dictStore.applyLocal('demo_order_status', current)
}

function showEmpty(type: EmptyType) {
  emptyMode.value = type
}

function handleRetry() {
  retried.value += 1
  emptyMode.value = ''
}

onMounted(() => {
  const raw = sessionStorage.getItem(STATE_KEY)
  if (raw) {
    try {
      const saved = JSON.parse(raw)
      searchForm.value = {
        name: saved.name || '',
        status: saved.status || '',
        orderNo: saved.orderNo || '',
        amount: saved.amount || '',
        idCard: saved.idCard || '',
        created: saved.created || '',
      }
      pageNo.value = saved.pageNo || 1
    } catch {
      sessionStorage.removeItem(STATE_KEY)
    }
  }
  if (sessionStorage.getItem('ims_slow_list') === '1') {
    loading.value = true
    window.setTimeout(() => {
      loading.value = false
      sessionStorage.removeItem('ims_slow_list')
    }, 2000)
  }
})

watch(pageNo, persist)
</script>

<template>
  <AppLayout>
    <div class="list-demo">
      <PageHeader title="列表演示" sub-title="FP-P-04 / UI-L01">
        <template #actions>
          <el-button type="primary" @click="handleCreate">新建</el-button>
          <el-button @click="refreshDict">刷新字典</el-button>
        </template>
        <template #primary-action>
          <el-button type="primary" @click="handleCreate">新建</el-button>
        </template>
      </PageHeader>

      <div class="query-bar">
        <el-form :model="searchForm" inline @submit.prevent="handleSearch">
          <el-form-item class="query-field" label="名称">
            <el-input v-model="searchForm.name" placeholder="请输入名称" clearable @keyup.enter="handleSearch" />
          </el-form-item>
          <el-form-item class="query-field" label="状态">
            <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 120px">
              <el-option label="草稿" value="DRAFT" />
              <el-option label="待审批" value="PENDING" />
              <el-option label="已通过" value="APPROVED" />
              <el-option label="已驳回" value="REJECTED" />
              <el-option label="已取消" value="CANCELLED" />
            </el-select>
          </el-form-item>
          <el-form-item class="query-field" label="订单号">
            <el-input v-model="searchForm.orderNo" placeholder="订单号" clearable @keyup.enter="handleSearch" />
          </el-form-item>
          <el-form-item class="query-field" label="金额">
            <el-input v-model="searchForm.amount" placeholder="金额" clearable />
          </el-form-item>
          <el-form-item v-show="showMore" class="query-field" label="证件号">
            <el-input v-model="searchForm.idCard" placeholder="证件号" clearable />
          </el-form-item>
          <el-form-item v-show="showMore" class="query-field" label="创建日期">
            <el-input v-model="searchForm.created" placeholder="创建日期" clearable />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
            <el-button @click="showMore = !showMore">{{ showMore ? '收起' : '更多' }}</el-button>
          </el-form-item>
        </el-form>
        <div v-if="chips.length" class="chip-row">
          <Chip v-for="chip in chips" :key="chip.key" :label="chip.label" @close="closeChip(chip.key)" />
        </div>
      </div>

      <div class="demo-switches">
        <el-button v-if="selected.length" type="warning">批量操作</el-button>
        <el-button size="small" @click="showEmpty('empty')">空数据</el-button>
        <el-button size="small" @click="showEmpty('noPermission')">无权限</el-button>
        <el-button size="small" @click="showEmpty('error')">加载失败</el-button>
        <span v-if="retried" class="retry-count">已重试 {{ retried }}</span>
      </div>

      <div v-loading="loading" class="table-wrap">
        <el-table
          v-if="!emptyMode"
          :data="tableData"
          style="width: 100%"
          @sort-change="handleSortChange"
          @selection-change="(rows: Order[]) => selected = rows"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="name" label="名称" min-width="120" fixed="left" show-overflow-tooltip />
          <el-table-column prop="orderNo" label="订单号" width="140">
            <template #default="{ row }">
              <span class="mono">{{ row.orderNo }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="金额" width="120" align="right" sortable="custom">
            <template #default="{ row }">
              <span :class="{ neg: row.amount < 0 }">{{ fmtMoney(row.amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <StatusTag dict-type="demo_order_status" :value="row.status" />
            </template>
          </el-table-column>
          <el-table-column prop="idCard" label="证件号" width="180">
            <template #default="{ row }">
              <span v-if="row.idCard" class="mono">{{ row.idCard }}</span>
              <span v-else class="empty-placeholder">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="cost" label="成本" width="100">
            <template #default="{ row }">
              <el-tooltip v-if="row.cost === '***'" content="无查看权限" placement="top" :trigger="isMobile ? 'click' : 'hover'">
                <span class="masked">***</span>
              </el-tooltip>
              <span v-else>{{ row.cost }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" width="160" />
          <el-table-column label="操作" :width="isMobile ? 72 : 200" fixed="right">
            <template #default="{ row }">
              <el-button v-if="!isMobile" text type="primary" size="small">编辑</el-button>
              <el-button v-if="!isMobile" text type="primary" size="small" @click="handleView(row)">查看</el-button>
              <el-dropdown trigger="click">
                <el-button text type="primary" size="small">更多</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="isMobile" @click="handleView(row)">查看</el-dropdown-item>
                    <el-dropdown-item v-if="isMobile" @click="handleCreate">编辑</el-dropdown-item>
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
        <EmptyState v-else :type="emptyMode" @retry="handleRetry" />
      </div>

      <Pagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" />

      <FormDrawer
        v-model:open="drawerVisible"
        :title="drawerTitle"
        size="M"
        :submit="handleSubmit"
      >
        <el-form :model="formModel" label-width="80px">
          <el-form-item label="名称" required>
            <el-input v-model="formModel.name" placeholder="请输入名称" />
          </el-form-item>
          <el-form-item label="金额" required :error="amountError">
            <el-input v-model="amountText" placeholder="金额" @blur="checkAmount" />
          </el-form-item>
        </el-form>
      </FormDrawer>

      <DetailDrawer
        v-model="detailOpen"
        :title="detailRow?.name || '详情'"
        :tabs="[{ key: 'base', label: '基本信息' }, { key: 'log', label: '操作记录' }]"
        :active-tab="detailTab"
        @update:active-tab="detailTab = $event"
      >
        <p>{{ detailRow?.orderNo }}</p>
        <template #footer>
          <el-button @click="detailOpen = false">关闭</el-button>
        </template>
      </DetailDrawer>

      <el-dialog v-model="confirmOpen" title="确定删除" width="420px" :close-on-click-modal="false">
        <p>确定删除订单「{{ pendingDelete?.name }}」？</p>
        <p v-if="confirmError" class="danger-text">{{ confirmError }}</p>
        <template #footer>
          <el-button @click="confirmOpen = false">取消</el-button>
          <el-button type="danger" @click="confirmDelete">确定</el-button>
        </template>
      </el-dialog>
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
    margin-bottom: 12px;
    margin-right: 16px;
  }

  :deep(.el-input) {
    width: 180px;
  }
}

.chip-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.demo-switches {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.table-wrap {
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  overflow: hidden;
  min-height: 120px;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
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

.retry-count {
  font-size: 12px;
  color: var(--text2);
}
</style>
