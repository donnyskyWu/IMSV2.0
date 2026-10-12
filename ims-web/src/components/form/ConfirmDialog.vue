<script setup lang="ts">
/**
 * ConfirmDialog 确认框
 * 依据: FP-C16-01, 00-工作包 §2.1 Q7
 * Q7: Modal 宽度 = min(档位, 100vw - 32px)
 */
import { ref, computed } from 'vue'
import { useResponsive, getModalWidth } from '@/utils/responsive'

interface Props {
  open: boolean
  title?: string
  message: string
  okText?: string
  danger?: boolean
  reasonRequired?: boolean
  reasonLabel?: string
  reasonMax?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '确认',
  okText: '确定',
  danger: false,
  reasonRequired: false,
  reasonLabel: '原因',
  reasonMax: 200,
  loading: false,
})

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'confirm', payload: { reason?: string }): void
  (e: 'cancel'): void
}>()

const { isMobile } = useResponsive()

// 原因输入
const reason = ref('')

// 弹窗宽度 (Q7)
const dialogWidth = computed(() => `${getModalWidth(360)}px`)

// 确定按钮是否可用
const canConfirm = computed(() => {
  if (props.reasonRequired) {
    return reason.value.trim().length > 0 && reason.value.length <= props.reasonMax
  }
  return true
})

// 确定
function handleConfirm() {
  emit('confirm', { reason: reason.value || undefined })
}

// 取消
function handleCancel() {
  reason.value = ''
  emit('update:open', false)
  emit('cancel')
}

// 关闭后重置
function handleClosed() {
  reason.value = ''
}
</script>

<template>
  <el-dialog
    :model-value="open"
    :title="title"
    :width="dialogWidth"
    :close-on-click-modal="false"
    :show-close="!loading"
    class="confirm-dialog"
    @update:model-value="emit('update:open', $event)"
    @closed="handleClosed"
  >
    <div class="confirm-content">
      <p class="confirm-message">{{ message }}</p>

      <div v-if="reasonRequired" class="confirm-reason">
        <label class="reason-label">
          {{ reasonLabel }}
          <span class="required">*</span>
        </label>
        <el-input
          v-model="reason"
          type="textarea"
          :rows="3"
          :maxlength="reasonMax"
          show-word-limit
          :placeholder="`请输入${reasonLabel}`"
        />
      </div>
    </div>

    <template #footer>
      <div class="confirm-footer">
        <el-button :disabled="loading" @click="handleCancel">取消</el-button>
        <el-button
          :type="danger ? 'danger' : 'primary'"
          :loading="loading"
          :disabled="!canConfirm"
          @click="handleConfirm"
        >
          {{ okText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.confirm-dialog {
  :deep(.el-dialog__header) {
    padding: 16px 20px;
    margin-right: 0;
  }

  :deep(.el-dialog__body) {
    padding: 20px;
  }

  :deep(.el-dialog__footer) {
    padding: 12px 20px;
  }
}

.confirm-content {
  font-size: 14px;
  color: var(--text);
}

.confirm-message {
  margin: 0 0 16px;
  line-height: 1.6;
}

.confirm-reason {
  margin-top: 16px;
}

.reason-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text2);
  margin-bottom: 8px;
}

.required {
  color: var(--red);
  margin-left: 2px;
}

.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
