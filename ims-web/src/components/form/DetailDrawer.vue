<script setup lang="ts">
/**
 * DetailDrawer 详情抽屉
 * 依据: FP-C09-01, 00-工作包 §2.1 Q5, Q6
 * 桌面: 侧边抽屉 600px
 * 手机 (Q5/Q6): 100% 全屏
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'
import StatusTag from '@/components/list/StatusTag.vue'

interface Tab {
  key: string
  label: string
}

interface Props {
  modelValue: boolean
  title?: string
  statusType?: string
  statusValue?: string
  tabs?: Tab[]
  activeTab?: string
  size?: string | number
}

const props = withDefaults(defineProps<Props>(), {
  title: '详情',
  size: 600,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'update:activeTab', tab: string): void
  (e: 'close'): void
}>()

const { isMobile } = useResponsive()

// 计算抽屉宽度 (Q6: 手机 100%)
const drawerSize = computed(() => {
  if (isMobile.value) return '100%'
  if (typeof props.size === 'number') return `${props.size}px`
  return props.size
})

// 控制显示
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

// 标签切换
function handleTabChange(tab: string) {
  emit('update:activeTab', tab)
}

function handleClose() {
  emit('close')
  visible.value = false
}
</script>

<template>
  <el-drawer
    v-model="visible"
    :size="drawerSize"
    :show-close="true"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    direction="rtl"
    class="detail-drawer"
    :class="{ 'detail-drawer--mobile': isMobile }"
    @close="handleClose"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">{{ title }}</span>
        <StatusTag
          v-if="statusType && statusValue"
          :dict-type="statusType"
          :value="statusValue"
        />
      </div>
    </template>

    <!-- 标签页 -->
    <div v-if="tabs && tabs.length > 1" class="drawer-tabs">
      <el-tabs
        :model-value="activeTab"
        @update:model-value="handleTabChange($event as string)"
      >
        <el-tab-pane
          v-for="tab in tabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
        />
      </el-tabs>
    </div>

    <!-- 内容 -->
    <div class="drawer-body">
      <slot />
    </div>

    <!-- 底部操作 -->
    <template v-if="$slots.footer" #footer>
      <div class="drawer-footer">
        <slot name="footer" />
      </div>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
.detail-drawer {
  :deep(.el-drawer__header) {
    padding: 16px 20px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0;
  }

  :deep(.el-drawer__body) {
    padding: 0;
    display: flex;
    flex-direction: column;
  }

  :deep(.el-drawer__footer) {
    padding: 12px 20px;
    border-top: 1px solid var(--line);
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drawer-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.drawer-tabs {
  padding: 0 20px;
  border-bottom: 1px solid var(--line);

  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }
}

.drawer-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 移动端全屏
.detail-drawer--mobile {
  :deep(.el-drawer) {
    width: 100% !important;
  }

  .drawer-body {
    padding: 16px;
  }
}
</style>
