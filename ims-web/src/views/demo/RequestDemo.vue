<script setup lang="ts">
/**
 * 请求演示页 (FP-P-14)
 * 展示 API 请求、错误处理、Toast 等
 */
import { ref } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { toast } from '@/utils/toast'

// 加载状态
const loading = ref(false)

// 模拟请求
async function simulateRequest(type: 'success' | 'error' | 'timeout') {
  loading.value = true
  
  try {
    await new Promise((resolve, reject) => {
      setTimeout(() => {
        if (type === 'success') {
          resolve({ data: { message: '操作成功' } })
        } else if (type === 'error') {
          reject(new Error('服务器错误'))
        } else {
          reject(new Error('请求超时'))
        }
      }, 1500)
    })
    
    toast.success('请求成功')
  } catch (err) {
    const error = err as Error
    toast.error(error.message || '请求失败')
  } finally {
    loading.value = false
  }
}

// 测试 Toast 去重
function testToastDedupe() {
  // 连续调用相同内容
  toast.info('这条消息只会显示一次')
  toast.info('这条消息只会显示一次')
  toast.info('这条消息只会显示一次')
}

// 测试 Toast 队列
function testToastQueue() {
  toast.success('消息 1')
  toast.success('消息 2')
  toast.success('消息 3')
  toast.success('消息 4')
  toast.success('消息 5')
}

// 测试不同类型
function testToastTypes() {
  toast.success('成功提示')
  setTimeout(() => toast.warning('警告提示'), 200)
  setTimeout(() => toast.error('错误提示'), 400)
  setTimeout(() => toast.info('信息提示'), 600)
}
</script>

<template>
  <AppLayout>
    <div class="request-demo">
      <PageHeader title="请求与提示演示" sub-title="FP-P-14" />

      <div class="demo-section">
        <h3 class="section-title">1. 模拟 API 请求</h3>
        <div class="button-group">
          <el-button
            type="primary"
            :loading="loading"
            @click="simulateRequest('success')"
          >
            成功请求
          </el-button>
          <el-button
            type="warning"
            :loading="loading"
            @click="simulateRequest('error')"
          >
            错误请求
          </el-button>
          <el-button
            type="danger"
            :loading="loading"
            @click="simulateRequest('timeout')"
          >
            超时请求
          </el-button>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">2. Toast 提示</h3>
        <div class="button-group">
          <el-button @click="testToastTypes">不同类型</el-button>
          <el-button @click="testToastDedupe">去重测试</el-button>
          <el-button @click="testToastQueue">队列测试</el-button>
        </div>
        <div class="demo-tip">
          <p>• 不同类型：依次显示 success、warning、error、info</p>
          <p>• 去重测试：1s 内相同内容只显示一次</p>
          <p>• 队列测试：最多同时显示 3 条，其余排队</p>
        </div>
      </div>

      <div class="demo-section">
        <h3 class="section-title">3. 错误码说明</h3>
        <el-table :data="errorCodes" style="width: 100%">
          <el-table-column prop="code" label="错误码" width="100" />
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="description" label="说明" />
        </el-table>
      </div>
    </div>
  </AppLayout>
</template>

<script lang="ts">
const errorCodes = [
  { code: '0', name: '成功', description: '请求成功' },
  { code: '401', name: '未认证', description: '需要登录或 Token 已过期' },
  { code: '403', name: '无权限', description: '没有操作权限' },
  { code: '404', name: '未找到', description: '资源不存在' },
  { code: '1001', name: '字段错误', description: '表单校验失败，返回字段错误列表' },
  { code: '1002', name: '业务异常', description: '业务规则校验失败' },
  { code: '500', name: '服务器错误', description: '服务器内部错误' },
]
</script>

<style lang="scss" scoped>
.request-demo {
  max-width: 800px;
}

.demo-section {
  margin-bottom: 24px;
  padding: 24px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.demo-tip {
  margin-top: 16px;
  padding: 12px;
  background-color: var(--hover);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text2);

  p {
    margin: 4px 0;
  }
}
</style>
