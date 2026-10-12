<script setup lang="ts">
/**
 * QueryBar 查询栏
 * 依据: FP-C06-01, 00-工作包 §2.1 Q9
 * 桌面: 一行排布, 超过 collapseAfter 的条件收进"更多"
 * 手机 (Q9): 默认只显示 1 个条件, 其余收进"筛选"全屏抽屉
 */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Filter, Search, RefreshRight } from '@element-plus/icons-vue'
import { useResponsive } from '@/utils/responsive'
import type { QueryField } from '@/types'

interface Props {
  fields: QueryField[]
  modelValue: Record<string, unknown>
  collapseAfter?: number
}

const props = withDefaults(defineProps<Props>(), {
  collapseAfter: 4,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: Record<string, unknown>): void
  (e: 'search', val: Record<string, unknown>): void
  (e: 'reset'): void
}>()

const route = useRoute()
const router = useRouter()
const { isMobile } = useResponsive()

// 移动端筛选抽屉
const filterDrawerVisible = ref(false)

// 更多展开状态
const moreExpanded = ref(false)

// 可见字段 (桌面)
const visibleFields = computed(() => {
  if (moreExpanded.value) return props.fields
  return props.fields.slice(0, props.collapseAfter)
})

// 折叠字段 (桌面)
const collapsedFields = computed(() => {
  return props.fields.slice(props.collapseAfter)
})

// 移动端: 第一个字段直接显示
const firstField = computed(() => props.fields[0])
const restFields = computed(() => props.fields.slice(1))

// 本地表单值
const localModel = ref<Record<string, unknown>>({ ...props.modelValue })

// 同步外部值
watch(
  () => props.modelValue,
  (val) => {
    localModel.value = { ...val }
  },
  { deep: true }
)

// 更新字段值
function updateField(key: string, value: unknown) {
  localModel.value[key] = value
  emit('update:modelValue', { ...localModel.value })
}

// 查询
function handleSearch() {
  syncToUrl()
  emit('search', { ...localModel.value })
  if (isMobile.value) {
    filterDrawerVisible.value = false
  }
}

// 重置
function handleReset() {
  const empty: Record<string, unknown> = {}
  props.fields.forEach((f) => {
    empty[f.key] = f.type === 'daterange' ? [] : ''
  })
  localModel.value = empty
  emit('update:modelValue', empty)
  emit('reset')
  syncToUrl()
}

// URL 同步
function syncToUrl() {
  const query: Record<string, string> = {}
  for (const [key, val] of Object.entries(localModel.value)) {
    if (val !== '' && val !== null && val !== undefined) {
      if (Array.isArray(val) && val.length === 2) {
        query[`${key}Start`] = String(val[0])
        query[`${key}End`] = String(val[1])
      } else {
        query[key] = String(val)
      }
    }
  }
  router.replace({ query: { ...route.query, ...query, pageNo: '1' } })
}

// 从 URL 恢复条件
function restoreFromUrl() {
  const query = route.query
  props.fields.forEach((f) => {
    if (f.type === 'daterange') {
      const start = query[`${f.key}Start`]
      const end = query[`${f.key}End`]
      if (start && end) {
        localModel.value[f.key] = [String(start), String(end)]
      }
    } else if (query[f.key]) {
      localModel.value[f.key] = String(query[f.key])
    }
  })
  emit('update:modelValue', { ...localModel.value })
}

// 初始化时恢复
restoreFromUrl()

// 已选条件数
const activeFilterCount = computed(() => {
  return Object.values(localModel.value).filter((v) => {
    if (Array.isArray(v)) return v.length > 0
    return v !== '' && v !== null && v !== undefined
  }).length
})
</script>

<template>
  <div class="query-bar" :class="{ 'query-bar--mobile': isMobile }">
    <!-- 桌面端 -->
    <template v-if="!isMobile">
      <el-form :model="localModel" inline @submit.prevent="handleSearch">
        <el-form-item
          v-for="field in visibleFields"
          :key="field.key"
          :label="field.label"
        >
          <!-- 输入框 -->
          <el-input
            v-if="field.type === 'input'"
            :model-value="localModel[field.key] as string"
            :placeholder="field.placeholder || `请输入${field.label}`"
            clearable
            class="query-input"
            @update:model-value="updateField(field.key, $event)"
            @keyup.enter="handleSearch"
          />

          <!-- 下拉选择 -->
          <el-select
            v-else-if="field.type === 'select'"
            :model-value="localModel[field.key]"
            :placeholder="field.placeholder || '全部'"
            clearable
            class="query-select"
            @update:model-value="updateField(field.key, $event)"
          >
            <el-option
              v-for="opt in field.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>

          <!-- 字典选择 -->
          <el-select
            v-else-if="field.type === 'dict'"
            :model-value="localModel[field.key]"
            :placeholder="field.placeholder || '全部'"
            clearable
            class="query-select"
            @update:model-value="updateField(field.key, $event)"
          >
            <el-option
              v-for="opt in field.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>

          <!-- 日期 -->
          <el-date-picker
            v-else-if="field.type === 'date'"
            :model-value="localModel[field.key] as string"
            type="date"
            :placeholder="field.placeholder || '选择日期'"
            value-format="YYYY-MM-DD"
            class="query-date"
            @update:model-value="updateField(field.key, $event)"
          />

          <!-- 日期范围 -->
          <el-date-picker
            v-else-if="field.type === 'daterange'"
            :model-value="localModel[field.key] as [string, string]"
            type="daterange"
            range-separator="~"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            class="query-daterange"
            @update:model-value="updateField(field.key, $event)"
          />
        </el-form-item>

        <!-- 更多展开按钮 -->
        <el-form-item v-if="collapsedFields.length > 0 && !moreExpanded">
          <el-button text type="primary" @click="moreExpanded = true">
            更多
            <el-icon class="el-icon--right"><Filter /></el-icon>
          </el-button>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshRight /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </template>

    <!-- 移动端 (Q9) -->
    <template v-else>
      <div class="mobile-query-row">
        <!-- 第一个条件直接显示 -->
        <div v-if="firstField" class="mobile-first-field">
          <el-input
            v-if="firstField.type === 'input'"
            :model-value="localModel[firstField.key] as string"
            :placeholder="firstField.placeholder || `搜索${firstField.label}`"
            clearable
            @update:model-value="updateField(firstField.key, $event)"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select
            v-else-if="firstField.type === 'select' || firstField.type === 'dict'"
            :model-value="localModel[firstField.key]"
            :placeholder="firstField.placeholder || '全部'"
            clearable
            @update:model-value="updateField(firstField.key, $event)"
          >
            <el-option
              v-for="opt in firstField.options"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </div>

        <!-- 筛选按钮 -->
        <el-button
          v-if="restFields.length > 0"
          class="filter-btn touch-target"
          @click="filterDrawerVisible = true"
        >
          <el-icon><Filter /></el-icon>
          筛选
          <el-badge
            v-if="activeFilterCount > 1"
            :value="activeFilterCount - 1"
            class="filter-badge"
          />
        </el-button>
      </div>

      <!-- 筛选抽屉 (全屏) -->
      <el-drawer
        v-model="filterDrawerVisible"
        title="筛选条件"
        direction="rtl"
        size="100%"
        class="filter-drawer"
      >
        <el-form :model="localModel" label-position="top">
          <el-form-item
            v-for="field in restFields"
            :key="field.key"
            :label="field.label"
          >
            <el-input
              v-if="field.type === 'input'"
              :model-value="localModel[field.key] as string"
              :placeholder="field.placeholder || `请输入${field.label}`"
              clearable
              @update:model-value="updateField(field.key, $event)"
            />
            <el-select
              v-else-if="field.type === 'select' || field.type === 'dict'"
              :model-value="localModel[field.key]"
              :placeholder="field.placeholder || '全部'"
              clearable
              style="width: 100%"
              @update:model-value="updateField(field.key, $event)"
            >
              <el-option
                v-for="opt in field.options"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-date-picker
              v-else-if="field.type === 'date'"
              :model-value="localModel[field.key] as string"
              type="date"
              :placeholder="field.placeholder || '选择日期'"
              value-format="YYYY-MM-DD"
              style="width: 100%"
              @update:model-value="updateField(field.key, $event)"
            />
            <el-date-picker
              v-else-if="field.type === 'daterange'"
              :model-value="localModel[field.key] as [string, string]"
              type="daterange"
              range-separator="~"
              start-placeholder="开始"
              end-placeholder="结束"
              value-format="YYYY-MM-DD"
              style="width: 100%"
              @update:model-value="updateField(field.key, $event)"
            />
          </el-form-item>
        </el-form>

        <template #footer>
          <div class="drawer-footer">
            <el-button @click="handleReset">重置</el-button>
            <el-button type="primary" @click="handleSearch">确定</el-button>
          </div>
        </template>
      </el-drawer>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.query-bar {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;

    &:last-child {
      margin-right: 0;
    }
  }
}

.query-input {
  width: 180px;
}

.query-select {
  width: 140px;
}

.query-date {
  width: 140px;
}

.query-daterange {
  width: 240px;
}

// 移动端
.query-bar--mobile {
  padding: 12px;

  .mobile-query-row {
    display: flex;
    gap: 8px;
  }

  .mobile-first-field {
    flex: 1;
    min-width: 0;
  }

  .filter-btn {
    flex-shrink: 0;
    position: relative;
  }

  .filter-badge {
    position: absolute;
    top: -4px;
    right: -4px;

    :deep(.el-badge__content) {
      height: 16px;
      line-height: 16px;
      padding: 0 4px;
      font-size: 10px;
    }
  }
}

.filter-drawer {
  :deep(.el-drawer__body) {
    padding: 16px;
  }

  :deep(.el-form-item) {
    margin-bottom: 16px;
  }
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
