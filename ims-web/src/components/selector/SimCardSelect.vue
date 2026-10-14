<script setup lang="ts">
/**
 * 手机卡选择器。只含启用卡，不能手输 id。版本 v1.0 · 2026-10-13
 */
import { onMounted, ref } from 'vue'
import { listSimOptions, type OptionRow } from '@/api/resource'

defineProps<{ modelValue?: string; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const options = ref<OptionRow[]>([])

async function load(keyword = '') {
  options.value = await listSimOptions(keyword)
}

onMounted(() => load())
</script>

<template>
  <el-select
    :model-value="modelValue"
    class="sim-select"
    filterable
    remote
    clearable
    :disabled="disabled"
    placeholder="请选择手机卡"
    :remote-method="load"
    @visible-change="(open: boolean) => open && load()"
    @update:model-value="emit('update:modelValue', $event || '')"
  >
    <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" />
  </el-select>
</template>
