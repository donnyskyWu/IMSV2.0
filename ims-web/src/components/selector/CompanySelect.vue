<script setup lang="ts">
/**
 * 公司选择器。只拉启用公司，不能手输 id。版本 v1.0 · 2026-10-13
 */
import { onMounted, ref } from 'vue'
import { listCompanyOptions, type OptionRow } from '@/api/resource'

defineProps<{ modelValue?: string; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const options = ref<OptionRow[]>([])

async function load(keyword = '') {
  options.value = await listCompanyOptions(keyword)
}

onMounted(() => load())
</script>

<template>
  <el-select
    :model-value="modelValue"
    class="company-select"
    filterable
    remote
    clearable
    :disabled="disabled"
    placeholder="请选择公司"
    :remote-method="load"
    @visible-change="(open: boolean) => open && load()"
    @update:model-value="emit('update:modelValue', $event || '')"
  >
    <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" />
  </el-select>
</template>
