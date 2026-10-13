<script setup lang="ts">
/**
 * 系统管理列表。原生表格，避免数据表格固定列把同一按钮画两份。
 */
import type { TableColumn } from '@/types'

defineProps<{
  columns: TableColumn[]
  data: Record<string, unknown>[]
}>()

function text(value: unknown) {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}
</script>

<template>
  <div class="plain-table">
    <table>
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in data" :key="String(row.id ?? index)">
          <td v-for="col in columns" :key="col.key">
            <slot v-if="$slots[`cell-${col.key}`]" :name="`cell-${col.key}`" :row="row" />
            <span v-else>{{ text(row[col.key]) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.plain-table {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 8px;
  border-bottom: 1px solid var(--line, #e5e7eb);
  text-align: left;
  vertical-align: top;
  white-space: nowrap;
}
</style>
