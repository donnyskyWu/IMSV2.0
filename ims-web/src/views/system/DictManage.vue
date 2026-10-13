<script setup lang="ts">
/** 字典（FP-B2-D） */
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import { ApiError } from '@/api/request'
import { systemAdminApi } from '@/api/system-admin'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const types = ref<Record<string, unknown>[]>([])
const values = ref<Record<string, unknown>[]>([])
const current = ref('')
const error = ref('')
const typeCode = ref('')
const typeName = ref('')
const dictValue = ref('')
const dictLabel = ref('')

const columns: TableColumn[] = [
  { key: 'sort', label: '排序' },
  { key: 'label', label: '标签' },
  { key: 'value', label: '值' },
  { key: 'colorType', label: '颜色预览' },
  { key: 'statusText', label: '状态' },
  { key: 'actions', label: '操作' },
]

async function loadTypes() {
  types.value = await systemAdminApi.dictTypes()
  if (!current.value && types.value[0]) current.value = String(types.value[0].dictType || '')
  if (current.value) await loadValues()
}

async function loadValues() {
  const list = await systemAdminApi.dictData(current.value)
  values.value = (list || []).map((row) => ({
    ...row,
    statusText: row.status === 'DISABLED' ? '停用' : '启用',
  }))
}

async function createType() {
  error.value = ''
  if (!/^dict_[a-z][a-z0-9_]*$/.test(typeCode.value)) {
    error.value = '字典类型格式错误'
    return
  }
  try {
    await systemAdminApi.dictTypeCreate({ dictType: typeCode.value, name: typeName.value })
    toast.success('保存成功')
    await loadTypes()
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败'
  }
}

async function createValue() {
  error.value = ''
  if (!/^[A-Z][A-Z0-9_]*$/.test(dictValue.value)) {
    error.value = '字典值格式错误'
    return
  }
  await systemAdminApi.dictDataCreate({
    dictType: current.value,
    dictValue: dictValue.value,
    label: dictLabel.value,
    colorType: 'success',
  })
  toast.success('保存成功')
  await loadValues()
}

async function disableValue(row: Record<string, unknown>) {
  await systemAdminApi.dictDataUpdate({ id: row.id, status: 'DISABLED' })
  await loadValues()
}

onMounted(loadTypes)
</script>

<template>
  <div data-testid="page-dict">
    <PageHeader title="字典" />
    <div class="split">
      <aside>
        <button
          v-for="item in types"
          :key="String(item.dictType)"
          type="button"
          :data-testid="`dict-type-${item.dictType}`"
          @click="current = String(item.dictType); loadValues()"
        >
          {{ item.name }} {{ item.dictType }}
        </button>
        <input v-model="typeCode" data-testid="field-dict-type" placeholder="dict_tc_type" />
        <input v-model="typeName" data-testid="field-dict-type-name" placeholder="名称" />
        <el-button data-testid="btn-dict-type" @click="createType">新建字典类型</el-button>
      </aside>
      <section>
        <p v-if="error" class="error" data-testid="dict-error">{{ error }}</p>
        <input v-model="dictValue" data-testid="field-dict-value" placeholder="字典值" />
        <input v-model="dictLabel" data-testid="field-dict-label" placeholder="标签" />
        <el-button data-testid="btn-dict-value" @click="createValue">新增字典值</el-button>
        <PlainTable :columns="columns" :data="values">
          <template #cell-colorType="{ row }">
            <span :data-testid="`color-${row.value}`" :class="String(row.colorType)">{{ row.colorType }}</span>
          </template>
          <template #cell-actions="{ row }">
            <el-button v-if="row.status !== 'DISABLED'" data-testid="btn-dict-disable" @click="disableValue(row)">停用</el-button>
          </template>
        </PlainTable>
      </section>
    </div>
  </div>
</template>

<style scoped>
.split {
  display: flex;
  gap: 16px;
}

aside {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  width: 280px;
}

.error {
  color: var(--danger, #c45656);
}

.success {
  color: var(--success, #67c23a);
}
</style>
