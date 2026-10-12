<script setup lang="ts">
/**
 * RemoteSelect 远程搜索选择器基座
 * 依据: FP-C15-01
 * - 防抖搜索 (300ms)
 * - 支持分页
 * - Echo 回显已选值
 * - 支持单选 / 多选
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useResponsive } from '@/utils/responsive'

interface SelectOption {
  value: string | number
  label: string
  [key: string]: unknown
}

interface Props {
  modelValue?: string | number | Array<string | number>
  placeholder?: string
  multiple?: boolean
  disabled?: boolean
  clearable?: boolean
  // 搜索函数: 返回 { list, total }
  fetchFn: (params: {
    keyword: string
    pageNo: number
    pageSize: number
  }) => Promise<{ list: SelectOption[]; total: number }>
  // 回显函数: 根据 value 获取完整选项
  echoFn?: (value: string | number | Array<string | number>) => Promise<SelectOption[]>
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请选择',
  multiple: false,
  disabled: false,
  clearable: true,
  pageSize: 20,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string | number | Array<string | number> | undefined): void
  (e: 'change', val: string | number | Array<string | number> | undefined, option: SelectOption | SelectOption[] | undefined): void
}>()

const { isMobile } = useResponsive()

// 选项列表
const options = ref<SelectOption[]>([])
const loading = ref(false)
const keyword = ref('')
const pageNo = ref(1)
const total = ref(0)
const hasMore = computed(() => options.value.length < total.value)

// 已回显的选项 (用于展示已选值)
const echoedOptions = ref<SelectOption[]>([])

// 合并选项 (防止已选值在搜索后丢失)
const mergedOptions = computed(() => {
  const map = new Map<string | number, SelectOption>()
  echoedOptions.value.forEach((o) => map.set(o.value, o))
  options.value.forEach((o) => map.set(o.value, o))
  return Array.from(map.values())
})

// 搜索
async function doSearch(resetPage = true) {
  if (resetPage) {
    pageNo.value = 1
    options.value = []
  }
  loading.value = true
  try {
    const res = await props.fetchFn({
      keyword: keyword.value,
      pageNo: pageNo.value,
      pageSize: props.pageSize,
    })
    if (pageNo.value === 1) {
      options.value = res.list
    } else {
      options.value = [...options.value, ...res.list]
    }
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// 防抖搜索
const debouncedSearch = useDebounceFn((val: string) => {
  keyword.value = val
  doSearch(true)
}, 300)

// 远程搜索
function handleRemoteSearch(val: string) {
  debouncedSearch(val)
}

// 加载更多
function handleLoadMore() {
  if (!hasMore.value || loading.value) return
  pageNo.value++
  doSearch(false)
}

// 滚动到底部加载
function handleScroll(e: Event) {
  const target = e.target as HTMLElement
  if (target.scrollHeight - target.scrollTop - target.clientHeight < 50) {
    handleLoadMore()
  }
}

// 回显已选值
async function echoSelectedValue() {
  if (!props.modelValue || !props.echoFn) return
  if (Array.isArray(props.modelValue) && props.modelValue.length === 0) return

  try {
    const res = await props.echoFn(props.modelValue)
    echoedOptions.value = res
  } catch {
    // 回显失败，忽略
  }
}

// 值变化
function handleChange(val: string | number | Array<string | number> | undefined) {
  emit('update:modelValue', val)
  
  // 查找对应的选项
  if (val === undefined || val === '') {
    emit('change', val, undefined)
  } else if (Array.isArray(val)) {
    const selected = mergedOptions.value.filter((o) => val.includes(o.value))
    emit('change', val, selected)
  } else {
    const selected = mergedOptions.value.find((o) => o.value === val)
    emit('change', val, selected)
  }
}

// 下拉展开时搜索
function handleVisibleChange(visible: boolean) {
  if (visible && options.value.length === 0) {
    doSearch(true)
  }
}

// 初始化回显
onMounted(() => {
  if (props.modelValue) {
    echoSelectedValue()
  }
})

// 监听外部值变化
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      echoSelectedValue()
    }
  }
)
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder"
    :multiple="multiple"
    :disabled="disabled"
    :clearable="clearable"
    :loading="loading"
    filterable
    remote
    reserve-keyword
    :remote-method="handleRemoteSearch"
    class="remote-select"
    :class="{ 'remote-select--mobile': isMobile }"
    @update:model-value="handleChange"
    @visible-change="handleVisibleChange"
  >
    <template #default>
      <div
        class="options-container"
        @scroll="handleScroll"
      >
        <el-option
          v-for="opt in mergedOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        >
          <slot name="option" :option="opt">
            {{ opt.label }}
          </slot>
        </el-option>

        <el-option v-if="loading && pageNo > 1" disabled value="">
          <span class="loading-more">加载中...</span>
        </el-option>
      </div>
    </template>

    <template v-if="$slots.prefix" #prefix>
      <slot name="prefix" />
    </template>
  </el-select>
</template>

<style lang="scss" scoped>
.remote-select {
  width: 100%;
}

.options-container {
  max-height: 160px;
  overflow-y: auto;
}

.loading-more {
  color: var(--text2);
  font-size: 12px;
}

// 移动端
.remote-select--mobile {
  :deep(.el-select__wrapper) {
    min-height: var(--min-touch-size);
  }
}
</style>
