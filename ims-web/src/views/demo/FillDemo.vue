<script setup lang="ts">
/**
 * 填充页演示 (FP-P-13)
 * 用于展示空状态等
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { toast } from '@/utils/toast'

const emptyType = ref<'empty' | 'noPermission' | 'error'>('empty')

function handleRetry() {
  console.log('Retry clicked')
}

const submitting = ref(false)
const submitCount = ref(0)

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  try {
    await new Promise((resolve) => setTimeout(resolve, 400))
    submitCount.value += 1
    toast.success('提交成功')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppLayout hide-sidebar>
    <div class="fill-demo">
      <PageHeader title="空状态演示" sub-title="FP-P-13" />

      <div class="demo-section">
        <div class="type-selector">
          <el-radio-group v-model="emptyType">
            <el-radio-button value="empty">空数据</el-radio-button>
            <el-radio-button value="noPermission">无权限</el-radio-button>
            <el-radio-button value="error">加载错误</el-radio-button>
          </el-radio-group>
        </div>

        <div class="empty-container">
          <EmptyState :type="emptyType" @retry="handleRetry" />
        </div>
      </div>
      <div class="fill-footer">
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
        <span class="submit-count">已提交 {{ submitCount }}</span>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.fill-demo {
  max-width: 800px;
}

.demo-section {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 24px;
}

.type-selector {
  margin-bottom: 24px;
  text-align: center;
}

.fill-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 0;
  background: var(--bg);
}

.empty-container {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--hover);
  border-radius: var(--r-s);
}
</style>
