<script setup lang="ts">
/**
 * 实名人选择器。只含在职人员，不能手输 id。版本 v1.0 · 2026-10-13
 */
import { onMounted, ref } from 'vue'
import { listRealnameOptions, type OptionRow } from '@/api/resource'

defineProps<{ modelValue?: string; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const options = ref<OptionRow[]>([])

async function load(keyword = '') {
  options.value = await listRealnameOptions(keyword)
}

onMounted(() => load())
</script>

<template>
  <!-- 不开启可搜索，输入框只读，避免把手输的 id 当成实名人。 -->
  <el-select
    :model-value="modelValue"
    class="realname-select"
    clearable
    :disabled="disabled"
    placeholder="请选择实名人"
    @visible-change="(open: boolean) => open && load()"
    @update:model-value="emit('update:modelValue', $event || '')"
  >
    <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" />
  </el-select>
</template>
