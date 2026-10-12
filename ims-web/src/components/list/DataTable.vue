<script setup lang="ts">
/**
 * DataTable 数据表格
 * 依据: FP-C07-01, 00-工作包 §2.1 Q4, §2.2 #10
 * 桌面: 行操作超过 3 个时第 4 个起收进"更多"
 * 手机 (Q4): 横向滚动，首列和操作列固定，操作列只留"更多"
 * §2.2 #10: 手机下首列宽度不超过 120px，超出部分省略并提供 tooltip
 */
import { computed, useSlots } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'
import { useDictStore } from '@/stores/dict'
import { fmtMoney, fmtPercent, fmtTime, emptyPlaceholder } from '@/utils/format'
import StatusTag from './StatusTag.vue'
import EmptyState from './EmptyState.vue'
import type { TableColumn } from '@/types'

interface Props {
  columns: TableColumn[]
  data: Record<string, unknown>[]
  loading?: boolean
  selectable?: boolean
  rowKey?: string
  emptyType?: 'empty' | 'noPermission' | 'error'
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectable: false,
  rowKey: 'id',
  emptyType: 'empty',
})

const emit = defineEmits<{
  (e: 'sort-change', payload: { sortField: string; sortOrder: 'asc' | 'desc' | '' }): void
  (e: 'selection-change', rows: Record<string, unknown>[]): void
  (e: 'retry'): void
}>()

const slots = useSlots()
const { isMobile } = useResponsive()
const dictStore = useDictStore()

// 处理排序变化
function handleSortChange({ prop, order }: { prop: string; order: string | null }) {
  emit('sort-change', {
    sortField: prop || '',
    sortOrder: order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : '',
  })
}

// 处理选择变化
function handleSelectionChange(rows: Record<string, unknown>[]) {
  emit('selection-change', rows)
}

// 格式化单元格值
function formatCellValue(row: Record<string, unknown>, col: TableColumn): string {
  const value = row[col.key]
  if (value === null || value === undefined || value === '') {
    return emptyPlaceholder()
  }

  switch (col.type) {
    case 'money':
      return fmtMoney(value)
    case 'percent':
      return fmtPercent(value as number)
    case 'time':
      return fmtTime(value as string)
    case 'mono':
      return String(value)
    default:
      return String(value)
  }
}

// 是否负数 (用于金额红色显示)
function isNegative(value: unknown): boolean {
  return typeof value === 'number' && value < 0
}

// 获取首列宽度
const firstColumnWidth = computed(() => {
  return isMobile.value ? 120 : undefined
})
</script>

<template>
  <div class="data-table-wrap" :class="{ 'data-table--mobile': isMobile }">
    <el-table
      v-loading="loading"
      :data="data"
      :row-key="rowKey"
      style="width: 100%"
      :scrollbar-always-on="isMobile"
      @sort-change="handleSortChange"
      @selection-change="handleSelectionChange"
    >
      <!-- 选择列 -->
      <el-table-column
        v-if="selectable"
        type="selection"
        width="50"
        :fixed="isMobile ? 'left' : false"
      />

      <!-- 数据列 -->
      <el-table-column
        v-for="(col, index) in columns"
        :key="col.key"
        :prop="col.key"
        :label="col.label"
        :width="index === 0 ? firstColumnWidth : col.width"
        :min-width="col.minWidth"
        :align="col.type === 'number' || col.type === 'money' || col.type === 'percent' ? 'right' : undefined"
        :sortable="col.sortable ? 'custom' : false"
        :fixed="index === 0 && isMobile ? 'left' : col.fixed"
        :show-overflow-tooltip="index === 0 && isMobile"
      >
        <template #default="{ row }">
          <!-- 自定义插槽 -->
          <slot v-if="slots[`cell-${col.key}`]" :name="`cell-${col.key}`" :row="row" />

          <!-- 状态标签 -->
          <StatusTag
            v-else-if="col.type === 'status' && col.dictType"
            :dict-type="col.dictType"
            :value="row[col.key] as string"
          />

          <!-- 脱敏值 -->
          <template v-else-if="col.type === 'masked'">
            <el-tooltip
              v-if="row[col.key] === '***'"
              content="无查看权限"
              placement="top"
            >
              <span class="masked-text">***</span>
            </el-tooltip>
            <span v-else class="mono">{{ row[col.key] || emptyPlaceholder() }}</span>
          </template>

          <!-- 等宽字体 -->
          <span v-else-if="col.type === 'mono'" class="mono">
            {{ formatCellValue(row, col) }}
          </span>

          <!-- 金额 -->
          <span
            v-else-if="col.type === 'money'"
            :class="{ neg: isNegative(row[col.key]) }"
            class="num"
          >
            {{ formatCellValue(row, col) }}
          </span>

          <!-- 其他 -->
          <span v-else>{{ formatCellValue(row, col) }}</span>
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column
        v-if="slots.actions"
        label="操作"
        :width="isMobile ? 80 : 160"
        fixed="right"
        class-name="actions-column"
      >
        <template #default="{ row }">
          <!-- 桌面端: 显示前 3 个按钮 + 更多 -->
          <template v-if="!isMobile">
            <slot name="actions" :row="row" />
          </template>

          <!-- 移动端 (Q4): 只显示"更多"下拉 -->
          <template v-else>
            <el-dropdown trigger="click">
              <el-button class="more-btn touch-target" text type="primary">
                <span>更多</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <slot name="mobile-actions" :row="row">
                    <slot name="actions" :row="row" />
                  </slot>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </template>
      </el-table-column>

      <!-- 空状态 -->
      <template #empty>
        <EmptyState
          :type="emptyType"
          @retry="emit('retry')"
        />
      </template>
    </el-table>
  </div>
</template>

<style lang="scss" scoped>
.data-table-wrap {
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  overflow: hidden;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
}

.num {
  font-variant-numeric: tabular-nums;
}

.neg {
  color: var(--red);
}

.masked-text {
  color: var(--text2);
  cursor: help;
}

// 移动端
.data-table--mobile {
  :deep(.el-table) {
    // 首列最大宽度 120px (§2.2 #10)
    .el-table-fixed-column--left {
      max-width: 120px;

      .cell {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .more-btn {
    padding: 8px 12px;
  }
}

// 操作列按钮
:deep(.actions-column) {
  .cell {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }
}
</style>
