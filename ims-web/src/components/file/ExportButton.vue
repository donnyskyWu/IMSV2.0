<script setup lang="ts">
/**
 * ExportButton 导出按钮
 * 依据: FP-C18-02
 * - 显示导出选项
 * - 进度提示
 */
import { ref } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { toast } from '@/utils/toast'

interface ExportOption {
  label: string
  value: string
  format?: string
}

interface Props {
  options?: ExportOption[]
  disabled?: boolean
  loading?: boolean
  filename?: string
}

const props = withDefaults(defineProps<Props>(), {
  options: () => [
    { label: '导出当前页', value: 'current', format: 'xlsx' },
    { label: '导出全部', value: 'all', format: 'xlsx' },
    { label: '导出为 CSV', value: 'csv', format: 'csv' },
  ],
  disabled: false,
  loading: false,
  filename: '导出数据',
})

const emit = defineEmits<{
  (e: 'export', option: ExportOption): void
}>()

const exporting = ref(false)

async function handleExport(option: ExportOption) {
  exporting.value = true
  toast.info('正在导出，请稍候...')
  
  emit('export', option)

  // 模拟导出延迟
  await new Promise((r) => setTimeout(r, 1500))
  
  exporting.value = false
  toast.success('导出成功')
}
</script>

<template>
  <el-dropdown
    trigger="click"
    :disabled="disabled || exporting"
    @command="handleExport"
  >
    <el-button :loading="exporting || loading" :disabled="disabled">
      <el-icon><Download /></el-icon>
      导出
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="opt in options"
          :key="opt.value"
          :command="opt"
        >
          {{ opt.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>
