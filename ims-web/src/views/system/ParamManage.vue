<script setup lang="ts">
/** 参数（FP-B2-P） */
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PlainTable from '@/components/list/PlainTable.vue'
import { systemAdminApi } from '@/api/system-admin'
import { toast } from '@/utils/toast'
import type { TableColumn } from '@/types'

const groups = ['内容审核', '钉钉', '钉钉考勤', 'AI', '通用']
const group = ref('内容审核')
const rows = ref<Record<string, unknown>[]>([])
const draft = ref<Record<string, string>>({})

const columns: TableColumn[] = [
  { key: 'name', label: '参数名' },
  { key: 'paramKey', label: 'key' },
  { key: 'valueType', label: '类型' },
  { key: 'displayValue', label: '当前值' },
  { key: 'defaultValue', label: '默认值' },
  { key: 'remark', label: '说明' },
  { key: 'actions', label: '操作' },
]

const shown = computed(() => rows.value.map((row) => ({
  ...row,
  displayValue: row.valueType === 'SECRET' ? '******' : row.value,
})))

const hasTraining = computed(() => rows.value.some((row) => String(row.paramKey || '').includes('training')))

async function load() {
  rows.value = await systemAdminApi.paramList(group.value)
}

function onDraft(key: string, event: Event) {
  const target = event.target as { value?: string } | null
  draft.value[key] = target?.value || ''
}

async function save(row: Record<string, unknown>) {
  const key = String(row.paramKey)
  await systemAdminApi.paramUpdate({ paramKey: key, value: draft.value[key] ?? String(row.value ?? '') })
  toast.success('参数已更新')
  await load()
}

onMounted(load)
</script>

<template>
  <div data-testid="page-param">
    <PageHeader title="参数" />
    <div class="groups">
      <button v-for="item in groups" :key="item" type="button" :data-testid="`param-group-${item}`" @click="group = item; load()">
        {{ item }}
      </button>
    </div>
    <p v-if="hasTraining" data-testid="training-flag">培训 AI</p>
    <PlainTable :columns="columns" :data="shown">
      <template #cell-actions="{ row }">
        <input :data-testid="`param-value-${row.paramKey}`" :value="draft[String(row.paramKey)] ?? ''" @input="onDraft(String(row.paramKey), $event)" />
        <el-button data-testid="btn-param-save" @click="save(row)">修改</el-button>
      </template>
    </PlainTable>
  </div>
</template>

<style scoped>
.groups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
