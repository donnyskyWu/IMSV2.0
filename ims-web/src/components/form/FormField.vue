<script setup lang="ts">
/**
 * FormField 表单项
 * 依据: FP-C17-01, 00-工作包 §2.1 Q5
 * 桌面: 两列布局
 * 手机 (Q5): 改成单列，标签放在输入框上方
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'

interface Props {
  label: string
  prop?: string
  required?: boolean
  span?: 1 | 2
  help?: string
}

const props = withDefaults(defineProps<Props>(), {
  required: false,
  span: 1,
})

const { isMobile } = useResponsive()

// 手机端强制 span=2 (单列)
const actualSpan = computed(() => (isMobile.value ? 2 : props.span))
</script>

<template>
  <el-form-item
    :label="label"
    :prop="prop"
    :required="required"
    class="form-field"
    :class="[`form-field--span-${actualSpan}`, { 'form-field--mobile': isMobile }]"
  >
    <slot />
    <template v-if="help" #tip>
      <span class="field-help">{{ help }}</span>
    </template>
  </el-form-item>
</template>

<style lang="scss" scoped>
.form-field {
  margin-bottom: 18px;

  &--span-2 {
    grid-column: span 2;
  }

  // 手机端样式 (Q5)
  &--mobile {
    :deep(.el-form-item__label) {
      display: block;
      text-align: left;
      margin-bottom: 6px;
      padding-right: 0;
      line-height: 1.4;
    }

    :deep(.el-form-item__content) {
      flex-wrap: wrap;
    }
  }
}

.field-help {
  font-size: 12px;
  color: var(--text2);
  margin-top: 4px;
  display: block;
}
</style>
