<script setup lang="ts">
/**
 * PageHeader 页头
 * 依据: FP-C02-01, 00-工作包 §2.1 Q14
 * 桌面: 标题 28px
 * 手机 (Q14): 标题改为 20px; actions 只保留主按钮, 其余收进"更多"
 */
import { computed } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useResponsive } from '@/utils/responsive'

interface Props {
  title: string
  subTitle?: string
  showScope?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showScope: true,
})

const authStore = useAuthStore()
const { isMobile } = useResponsive()

const showDataScope = computed(() => {
  // Q3: 手机下"统计范围"移到用户菜单里, 页头不显示
  return props.showScope && !isMobile.value && authStore.dataScopeText
})
</script>

<template>
  <div class="page-header">
    <div class="header-main">
      <div class="title-area">
        <h1 class="page-title">{{ title }}</h1>
        <span v-if="subTitle" class="page-subtitle">{{ subTitle }}</span>
      </div>

      <!-- 桌面端: 统计范围显示在页头 -->
      <div v-if="showDataScope" class="data-scope">
        统计范围：{{ authStore.dataScopeText }}
      </div>
    </div>

    <!-- 操作区 -->
    <div class="header-actions">
      <!-- 桌面端: 显示所有 actions -->
      <template v-if="!isMobile">
        <slot name="actions" />
      </template>

      <!-- 手机端 (Q14): 只保留主按钮, 其余收进"更多" -->
      <template v-else>
        <slot name="primary-action" />
        <el-dropdown v-if="$slots.actions" trigger="click">
          <el-button class="touch-target" text>
            <el-icon :size="20"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <slot name="actions" />
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-area {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.6px;
  margin: 0;

  @include mobile {
    // Q14: 手机下标题改为 20px
    font-size: 20px;
  }
}

.page-subtitle {
  font-size: 13px;
  color: var(--text2);
}

.data-scope {
  font-size: 13px;
  color: var(--text2);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
