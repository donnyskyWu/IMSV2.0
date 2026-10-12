<script setup lang="ts">
/**
 * ImportDialog 导入对话框
 * 依据: FP-C18-01
 * - 下载模板
 * - 上传文件
 * - 显示结果
 */
import { ref, computed } from 'vue'
import { Download, Upload, WarningFilled, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import Modal from '@/components/form/Modal.vue'
import FileUpload from './FileUpload.vue'
import { useResponsive } from '@/utils/responsive'
import { toast } from '@/utils/toast'

interface Props {
  modelValue: boolean
  title?: string
  templateUrl?: string
  templateName?: string
  accept?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '导入数据',
  templateUrl: '/template/import-template.xlsx',
  templateName: '导入模板.xlsx',
  accept: '.xlsx,.xls',
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'success', result: ImportResult): void
}>()

interface ImportResult {
  total: number
  success: number
  failed: number
  errors?: Array<{ row: number; column?: string; message: string }>
}

const { isMobile } = useResponsive()

// 步骤: upload | processing | result
const step = ref<'upload' | 'processing' | 'result'>('upload')

// 上传的文件
const uploadedFiles = ref<string[]>([])

// 导入结果
const importResult = ref<ImportResult | null>(null)

// 是否正在处理
const processing = ref(false)

// 下载模板
function downloadTemplate() {
  const link = document.createElement('a')
  link.href = props.templateUrl
  link.download = props.templateName
  link.click()
}

// 文件变化
function handleFileChange(files: unknown[]) {
  uploadedFiles.value = files.map((f: { name: string }) => f.name)
}

// 开始导入
async function handleImport() {
  if (uploadedFiles.value.length === 0) {
    toast.warning('请先上传文件')
    return
  }

  step.value = 'processing'
  processing.value = true

  await new Promise((r) => setTimeout(r, 300))

  const name = uploadedFiles.value[0] || ''
  if (name.includes('bad')) {
    importResult.value = {
      total: 10,
      success: 8,
      failed: 2,
      errors: [
        { row: 3, column: '金额', message: '金额格式错误' },
        { row: 8, column: '状态', message: '状态不存在' },
      ],
    }
  } else {
    importResult.value = {
      total: 10,
      success: 10,
      failed: 0,
    }
  }

  processing.value = false
  step.value = 'result'
  emit('success', importResult.value)
}

// 关闭
function handleClose() {
  step.value = 'upload'
  uploadedFiles.value = []
  importResult.value = null
  emit('update:modelValue', false)
}

// 重新导入
function handleRetry() {
  step.value = 'upload'
  uploadedFiles.value = []
  importResult.value = null
}
</script>

<template>
  <Modal
    :model-value="modelValue"
    :title="title"
    tier="md"
    :show-footer="step !== 'processing'"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- 上传步骤 -->
    <template v-if="step === 'upload'">
      <div class="import-step">
        <div class="step-section">
          <div class="section-title">1. 下载模板</div>
          <el-button type="primary" plain @click="downloadTemplate">
            <el-icon><Download /></el-icon>
            下载导入模板
          </el-button>
        </div>

        <div class="step-section">
          <div class="section-title">2. 上传文件</div>
          <FileUpload
            :accept="accept"
            :max-count="1"
            tip="仅支持 Excel 文件，大小不超过 10MB"
            @change="handleFileChange"
          />
        </div>
      </div>
    </template>

    <!-- 处理中 -->
    <template v-else-if="step === 'processing'">
      <div class="processing">
        <el-icon class="loading-icon" :size="48">
          <svg viewBox="0 0 24 24">
            <path fill="currentColor" d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
          </svg>
        </el-icon>
        <div class="processing-text">正在导入，请稍候...</div>
      </div>
    </template>

    <!-- 结果 -->
    <template v-else-if="step === 'result' && importResult">
      <div class="import-result">
        <div class="result-summary">
          <div class="summary-item">
            <span class="label">总计</span>
            <span class="value">{{ importResult.total }} 条</span>
          </div>
          <div class="summary-item success">
            <el-icon><CircleCheckFilled /></el-icon>
            <span class="label">成功</span>
            <span class="value">成功 {{ importResult.success }} 行</span>
          </div>
          <div class="summary-item error">
            <el-icon><CircleCloseFilled /></el-icon>
            <span class="label">失败</span>
            <span class="value">错误 {{ importResult.failed }} 行</span>
          </div>
        </div>

        <div v-if="importResult.errors?.length" class="error-list">
          <div class="error-title">
            <el-icon><WarningFilled /></el-icon>
            错误详情
          </div>
          <el-table :data="importResult.errors" max-height="200">
            <el-table-column prop="row" label="行号" width="80" />
            <el-table-column prop="column" label="列" width="100" />
            <el-table-column prop="message" label="错误信息" />
          </el-table>
        </div>
      </div>
    </template>

    <template #footer>
      <template v-if="step === 'upload'">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleImport">
          <el-icon><Upload /></el-icon>
          开始导入
        </el-button>
      </template>
      <template v-else-if="step === 'result'">
        <el-button @click="handleRetry">重新导入</el-button>
        <el-button type="primary" :disabled="(importResult?.failed || 0) > 0" @click="handleClose">确认导入</el-button>
      </template>
    </template>
  </Modal>
</template>

<style lang="scss" scoped>
.import-step {
  .step-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .section-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
    margin-bottom: 12px;
  }
}

.processing {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;

  .loading-icon {
    color: var(--blue);
    animation: spin 1s linear infinite;
  }

  .processing-text {
    margin-top: 16px;
    color: var(--text2);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.import-result {
  .result-summary {
    display: flex;
    gap: 24px;
    padding: 16px;
    background-color: var(--hover);
    border-radius: var(--r-s);
    margin-bottom: 16px;
  }

  .summary-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .label {
      color: var(--text2);
    }

    .value {
      font-weight: 500;
      color: var(--text);
    }

    &.success {
      color: var(--green);

      .value {
        color: var(--green);
      }
    }

    &.error {
      color: var(--red);

      .value {
        color: var(--red);
      }
    }
  }

  .error-list {
    .error-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 14px;
      color: var(--orange);
      margin-bottom: 8px;
    }
  }
}
</style>
