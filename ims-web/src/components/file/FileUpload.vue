<script setup lang="ts">
/**
 * FileUpload 文件上传
 * 依据: FP-C17-01
 * - 支持拖拽上传
 * - 文件大小和类型限制
 * - 进度显示
 */
import { ref, computed } from 'vue'
import { UploadFilled, Plus, Delete } from '@element-plus/icons-vue'
import { toast } from '@/utils/toast'
import { useResponsive } from '@/utils/responsive'
import type { UploadFile, UploadRawFile } from 'element-plus'

interface Props {
  modelValue?: string[]
  accept?: string
  maxSize?: number // MB
  maxCount?: number
  listType?: 'text' | 'picture' | 'picture-card'
  tip?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  accept: '*',
  maxSize: 10,
  maxCount: 5,
  listType: 'text',
  disabled: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string[]): void
  (e: 'change', files: UploadFile[]): void
}>()

const { isMobile } = useResponsive()

// 文件列表
const fileList = ref<UploadFile[]>([])

// 提示文字
const tipText = computed(() => {
  if (props.tip) return props.tip
  return `最多上传 ${props.maxCount} 个文件，单个文件不超过 ${props.maxSize}MB`
})

// 上传前校验
function beforeUpload(file: UploadRawFile): boolean {
  // 检查文件大小
  const isLt = file.size / 1024 / 1024 < props.maxSize
  if (!isLt) {
    toast.error(`文件大小不能超过 ${props.maxSize}MB`)
    return false
  }

  // 检查文件数量
  if (fileList.value.length >= props.maxCount) {
    toast.error(`最多只能上传 ${props.maxCount} 个文件`)
    return false
  }

  return true
}

// 文件变化
function handleChange(file: UploadFile, files: UploadFile[]) {
  fileList.value = files
  emit('update:modelValue', files.map((f) => f.url || f.name))
  emit('change', files)
}

// 移除文件
function handleRemove(file: UploadFile, files: UploadFile[]) {
  fileList.value = files
  emit('update:modelValue', files.map((f) => f.url || f.name))
  emit('change', files)
}

// 模拟上传
function customUpload(options: { file: File; onProgress: (e: { percent: number }) => void; onSuccess: () => void }) {
  let progress = 0
  const interval = setInterval(() => {
    progress += 20
    options.onProgress({ percent: progress })
    if (progress >= 100) {
      clearInterval(interval)
      options.onSuccess()
    }
  }, 200)
}
</script>

<template>
  <div class="file-upload" :class="{ 'file-upload--mobile': isMobile }">
    <el-upload
      v-model:file-list="fileList"
      :accept="accept"
      :limit="maxCount"
      :list-type="listType"
      :before-upload="beforeUpload"
      :http-request="customUpload"
      :disabled="disabled"
      drag
      multiple
      @change="handleChange"
      @remove="handleRemove"
    >
      <template v-if="listType === 'picture-card'">
        <el-icon><Plus /></el-icon>
      </template>
      <template v-else>
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
      </template>
    </el-upload>
    <div v-if="tipText" class="upload-tip">{{ tipText }}</div>
  </div>
</template>

<style lang="scss" scoped>
.file-upload {
  width: 100%;
}

.upload-icon {
  font-size: 48px;
  color: var(--text2);
}

.upload-text {
  margin-top: 8px;
  color: var(--text2);
  font-size: 14px;

  em {
    color: var(--blue);
    font-style: normal;
  }
}

.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text2);
}

// 移动端
.file-upload--mobile {
  :deep(.el-upload-dragger) {
    padding: 20px;
  }

  .upload-icon {
    font-size: 36px;
  }

  .upload-text {
    font-size: 13px;
  }
}
</style>
