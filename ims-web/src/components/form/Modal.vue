<script setup lang="ts">
/**
 * Modal 模态对话框
 * 依据: FP-C-29
 * 桌面: 根据 tier 决定宽度 (sm: 400px, md: 560px, lg: 800px)
 * 手机: min(tier, 100vw - 32px)
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'

type ModalTier = 'sm' | 'md' | 'lg'

interface Props {
  modelValue: boolean
  title?: string
  tier?: ModalTier
  showFooter?: boolean
  confirmText?: string
  cancelText?: string
  confirmLoading?: boolean
  closeOnClickModal?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  tier: 'md',
  showFooter: true,
  confirmText: '确定',
  cancelText: '取消',
  confirmLoading: false,
  closeOnClickModal: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const { isMobile } = useResponsive()

// 不同 tier 对应的宽度
const tierWidths: Record<ModalTier, number> = {
  sm: 400,
  md: 560,
  lg: 800,
}

// 计算对话框宽度
const dialogWidth = computed(() => {
  const tierWidth = tierWidths[props.tier]
  if (isMobile.value) {
    // min(tier, 100vw - 32px)
    return '100%'
  }
  return `${tierWidth}px`
})

// 移动端最大宽度
const mobileMaxWidth = computed(() => {
  if (isMobile.value) {
    return `min(${tierWidths[props.tier]}px, calc(100vw - 32px))`
  }
  return undefined
})

// 控制显示
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  visible.value = false
}

function handleClose() {
  emit('cancel')
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="dialogWidth"
    :style="{ maxWidth: mobileMaxWidth }"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="true"
    :append-to-body="true"
    :destroy-on-close="true"
    class="modal-dialog"
    :class="{ 'modal-dialog--mobile': isMobile }"
    @close="handleClose"
  >
    <slot />

    <template v-if="showFooter" #footer>
      <div class="modal-footer">
        <slot name="footer">
          <el-button @click="handleCancel">{{ cancelText }}</el-button>
          <el-button
            type="primary"
            :loading="confirmLoading"
            @click="handleConfirm"
          >
            {{ confirmText }}
          </el-button>
        </slot>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
.modal-dialog {
  :deep(.el-dialog__header) {
    padding: 16px 20px;
    border-bottom: 1px solid var(--line);
    margin-right: 0;
  }

  :deep(.el-dialog__title) {
    font-size: 16px;
    font-weight: 500;
    color: var(--text);
  }

  :deep(.el-dialog__body) {
    padding: 20px;
  }

  :deep(.el-dialog__footer) {
    padding: 12px 20px;
    border-top: 1px solid var(--line);
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 移动端
.modal-dialog--mobile {
  :deep(.el-dialog) {
    margin: 16px;
  }

  :deep(.el-dialog__body) {
    padding: 16px;
  }
}
</style>
