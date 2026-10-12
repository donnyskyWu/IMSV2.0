<script setup lang="ts">
/**
 * StepsWizard 步骤向导
 * 依据: FP-C-32
 * 桌面: 水平步骤条
 * 手机: 简化为 "第 n / N 步"
 */
import { computed } from 'vue'
import { useResponsive } from '@/utils/responsive'

interface Step {
  title: string
  description?: string
}

interface Props {
  steps: Step[]
  current: number
  finishStatus?: 'success' | 'error' | 'wait' | 'process' | 'finish'
}

const props = withDefaults(defineProps<Props>(), {
  finishStatus: 'success',
})

const emit = defineEmits<{
  (e: 'update:current', step: number): void
}>()

const { isMobile } = useResponsive()

// 当前步骤标题
const currentStepTitle = computed(() => {
  return props.steps[props.current]?.title || ''
})

// 进度比例
const progress = computed(() => {
  return ((props.current + 1) / props.steps.length) * 100
})

// 上一步
function handlePrev() {
  if (props.current > 0) {
    emit('update:current', props.current - 1)
  }
}

// 下一步
function handleNext() {
  if (props.current < props.steps.length - 1) {
    emit('update:current', props.current + 1)
  }
}
</script>

<template>
  <div class="steps-wizard" :class="{ 'steps-wizard--mobile': isMobile }">
    <!-- 桌面端: 标准步骤条 -->
    <el-steps
      v-if="!isMobile"
      :active="current"
      :finish-status="finishStatus"
      align-center
    >
      <el-step
        v-for="(step, index) in steps"
        :key="index"
        :title="step.title"
        :description="step.description"
      />
    </el-steps>

    <!-- 移动端: 简化显示 -->
    <div v-else class="mobile-steps">
      <div class="step-info">
        <span class="step-number">第 {{ current + 1 }} / {{ steps.length }} 步</span>
        <span class="step-title">{{ currentStepTitle }}</span>
      </div>
      <el-progress
        :percentage="progress"
        :show-text="false"
        :stroke-width="4"
        color="var(--blue)"
      />
    </div>

    <!-- 内容插槽 -->
    <div class="steps-content">
      <slot :current="current" :step="steps[current]" />
    </div>

    <!-- 底部操作 -->
    <div v-if="$slots.footer" class="steps-footer">
      <slot name="footer" :prev="handlePrev" :next="handleNext" :current="current">
        <el-button v-if="current > 0" @click="handlePrev">上一步</el-button>
        <el-button
          v-if="current < steps.length - 1"
          type="primary"
          @click="handleNext"
        >
          下一步
        </el-button>
        <slot v-else name="finish-button" />
      </slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.steps-wizard {
  display: flex;
  flex-direction: column;

  :deep(.el-steps) {
    margin-bottom: 24px;
  }
}

.steps-content {
  flex: 1;
  min-height: 0;
}

.steps-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  margin-top: 24px;
  border-top: 1px solid var(--line);
}

// 移动端
.steps-wizard--mobile {
  .mobile-steps {
    margin-bottom: 16px;
  }

  .step-info {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .step-number {
    font-size: 12px;
    color: var(--text2);
    padding: 2px 8px;
    background-color: var(--hover);
    border-radius: 10px;
  }

  .step-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }
}
</style>
