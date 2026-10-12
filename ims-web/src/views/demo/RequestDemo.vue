<script setup lang="ts">
/**
 * 请求演示页 (FP-P-02)
 * 依据: 按钮触发各种错误码处理
 */
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

// 模拟请求成功
function handleSuccess() {
  ElMessage.success('请求成功')
}

// 模拟 1001 表单错误
function handle1001() {
  ElMessage.warning('表单校验失败（1001）: 名称、金额字段有误')
}

// 模拟 1008 无权限
function handle1008() {
  ElMessage.error('暂无权限')
}

// 模拟 1504 资源不可用
function handle1504() {
  ElMessage.warning('资源不可用（1504）')
}

// 模拟 5007 系统异常
function handle5007() {
  const traceId = 'abc12345'
  ElMessage.error(`系统繁忙，请稍后再试 问题编号：${traceId}`)
}

// 模拟超时
function handleTimeout() {
  ElMessage.error('网络异常，请检查网络后重试')
}

// 模拟 401 刷新成功
function handle401RefreshSuccess() {
  ElMessage.success('令牌已刷新，请求重放成功')
}

// 模拟 401 刷新失败
function handle401RefreshFail() {
  ElMessage.error('登录已失效，请重新登录')
}

// 模拟 1003 被挤下线
function handle1003() {
  ElMessage.error('您的账号已在其他设备登录，本设备已下线')
}
</script>

<template>
  <AppLayout>
    <div class="request-demo">
      <PageHeader title="请求演示" sub-title="FP-P-02" />

      <section class="demo-section">
        <h3>模拟请求响应</h3>
        <div class="btn-grid">
          <el-button type="primary" @click="handleSuccess">
            成功请求
          </el-button>
          <el-button @click="handle1001">
            1001 表单错误
          </el-button>
          <el-button @click="handle1008">
            1008 无权限
          </el-button>
          <el-button @click="handle1504">
            1504 资源不可用
          </el-button>
          <el-button type="danger" @click="handle5007">
            5007 系统异常
          </el-button>
          <el-button @click="handleTimeout">
            超时
          </el-button>
        </div>
      </section>

      <section class="demo-section">
        <h3>令牌刷新场景</h3>
        <div class="btn-grid">
          <el-button type="success" @click="handle401RefreshSuccess">
            401 刷新成功
          </el-button>
          <el-button type="warning" @click="handle401RefreshFail">
            401 刷新失败
          </el-button>
          <el-button type="danger" @click="handle1003">
            1003 被挤下线
          </el-button>
        </div>
      </section>

      <section class="demo-section">
        <h3>说明</h3>
        <div class="notes">
          <p>• 成功请求: 显示绿色提示"请求成功"</p>
          <p>• 1001 表单错误: 字段级红框提示，不弹 toast</p>
          <p>• 1008 无权限: 提示"暂无权限"，页面保持原样</p>
          <p>• 1504 资源不可用: 抽屉内则关闭抽屉并刷新列表</p>
          <p>• 5xxx 系统异常: 显示问题编号（traceId 前 8 位）</p>
          <p>• 超时/网络错误: 提示"网络异常，请检查网络后重试"</p>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.request-demo {
  max-width: 800px;
}

.demo-section {
  margin-bottom: 32px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
  }
}

.btn-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  @include mobile {
    gap: $small-btn-gap;
  }
}

.notes {
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  p {
    font-size: 13px;
    color: var(--text2);
    margin: 4px 0;
  }
}
</style>
