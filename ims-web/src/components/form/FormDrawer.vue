<script setup lang="ts">
/**
 * FormDrawer 表单抽屉
 * 依据: FP-C14-01, 00-工作包 §2.1 Q6
 * 桌面: S 480 / M 720 / L 880
 * 手机 (Q6): 100% 全屏
 */
import { ref, computed, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useResponsive, getDrawerWidth } from '@/utils/responsive'
import type { DrawerSize } from '@/types'

interface Props {
  open: boolean
  title: string
  size?: DrawerSize
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'M',
  loading: false,
})

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'save'): void
  (e: 'closed'): void
}>()

const { isMobile } = useResponsive()

// 是否有未保存修改
const isDirty = ref(false)

// 抽屉宽度
const drawerWidth = computed(() => getDrawerWidth(props.size))

// 标记为已修改
function markDirty() {
  isDirty.value = true
}

// 关闭抽屉
async function handleClose() {
  if (isDirty.value) {
    try {
      await ElMessageBox.confirm('有未保存的修改，确定离开吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return // 用户取消
    }
  }
  isDirty.value = false
  emit('update:open', false)
  emit('closed')
}

// 保存
function handleSave() {
  emit('save')
}

// 保存成功后重置脏标记
function resetDirty() {
  isDirty.value = false
}

// 监听打开状态，重置脏标记
watch(
  () => props.open,
  (val) => {
    if (val) {
      isDirty.value = false
    }
  }
)

// 暴露方法
defineExpose({
  markDirty,
  resetDirty,
})
</script>

<template>
  <el-drawer
    :model-value="open"
    :title="title"
    :size="drawerWidth"
    :close-on-click-modal="false"
    :close-on-press-escape="!isDirty"
    :before-close="handleClose"
    direction="rtl"
    class="form-drawer"
    :class="{ 'form-drawer--mobile': isMobile }"
  >
    <template #header>
      <div class="drawer-header">
        <span class="drawer-title">{{ title }}</span>
      </div>
    </template>

    <div class="drawer-body" @input="markDirty">
      <slot />
    </div>

    <template #footer>
      <div class="drawer-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSave">
          保存
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
.form-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 16px 20px;
    border-bottom: 1px solid var(--line);
  }

  :deep(.el-drawer__body) {
    padding: 20px;
    overflow-y: auto;
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
  font-weight: 600;
  color: var(--text);
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

// 手机端全屏
.form-drawer--mobile {
  :deep(.el-drawer) {
    width: 100% !important;
  }
}
</style>
