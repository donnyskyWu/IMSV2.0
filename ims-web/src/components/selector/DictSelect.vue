<script setup lang="ts">
/**
 * DictSelect 字典选择器
 * 依据: FP-C15-02
 * 从 dictStore 获取字典数据
 */
import { computed } from 'vue'
import { useDictStore } from '@/stores/dict'
import { useResponsive } from '@/utils/responsive'

interface Props {
  modelValue?: string | number
  dictType: string
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择',
  disabled: false,
  clearable: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | number | undefined): void
  (e: 'change', val: string | number | undefined): void
}>()

const dictStore = useDictStore()
const { isMobile } = useResponsive()

// 获取字典选项
const options = computed(() => {
  return dictStore.getDict(props.dictType)
})

function handleChange(val: string | number | undefined) {
  emit('update:modelValue', val)
  emit('change', val)
}
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="clearable"
    class="dict-select"
    :class="{ 'dict-select--mobile': isMobile }"
    @update:model-value="handleChange"
  >
    <el-option
      v-for="opt in options"
      :key="opt.value"
      :label="opt.label"
      :value="opt.value"
    />
  </el-select>
</template>

<style lang="scss" scoped>
.dict-select {
  width: 100%;
}

// 移动端
.dict-select--mobile {
  :deep(.el-select__wrapper) {
    min-height: var(--min-touch-size);
  }
}
</style>
