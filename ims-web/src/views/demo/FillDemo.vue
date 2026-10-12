<script setup lang="ts">
/**
 * 填报页演示 (FP-P-12 之一)
 * 依据: UI-L07 填报/作答页（无侧栏二级页）
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

// 表单数据
const formModel = ref({
  name: '',
  content: '',
  amount: 0,
})

// 提交状态
const submitting = ref(false)

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('提交成功')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="fill-demo">
    <!-- 顶栏 -->
    <header class="fill-topbar">
      <div class="topbar-title">填报页演示</div>
      <div class="topbar-subtitle">FP-P-12 / UI-L07</div>
    </header>

    <!-- 内容区 -->
    <main class="fill-content">
      <el-form :model="formModel" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="formModel.name" placeholder="请输入名称" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="formModel.content"
            type="textarea"
            :rows="4"
            placeholder="请输入内容"
          />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="formModel.amount" :precision="2" />
        </el-form-item>
      </el-form>
    </main>

    <!-- 底部固定提交栏 -->
    <footer class="fill-footer">
      <el-button @click="$router.back()">返回</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        提交
      </el-button>
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.fill-demo {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg);
}

.fill-topbar {
  height: var(--topbar-height);
  background-color: var(--card);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
  flex-shrink: 0;
}

.topbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.topbar-subtitle {
  font-size: 13px;
  color: var(--text2);
}

.fill-content {
  flex: 1;
  padding: var(--content-padding-y) var(--content-padding-x);
  padding-bottom: calc(60px + var(--content-padding-y)); // 为底部固定栏留空
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.fill-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background-color: var(--card);
  border-top: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  gap: 12px;
}
</style>
