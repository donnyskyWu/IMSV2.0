<script setup lang="ts">
/**
 * 表单演示页 (FP-P-06)
 * 依据: FormDrawer 三档宽度、FormField 全部规则、
 * ConfirmDialog（含必填原因）、Modal 三档、StepsWizard、Toast
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import ConfirmDialog from '@/components/form/ConfirmDialog.vue'

// 抽屉状态
const drawerSizeS = ref(false)
const drawerSizeM = ref(false)
const drawerSizeL = ref(false)

// 表单数据
const formModel = ref({
  name: '',
  phone: '',
  email: '',
  amount: 0,
  percent: 0,
  remark: '',
})

// 模拟提交
async function handleSubmit() {
  console.log('Submit:', formModel.value)
  return new Promise(resolve => setTimeout(resolve, 500))
}

function handleSaved() {
  ElMessage.success('保存成功')
}

// 确认框
const confirmRef = ref<InstanceType<typeof ConfirmDialog> | null>(null)

async function showConfirm() {
  try {
    await confirmRef.value?.confirm({
      title: '确认操作',
      message: '确定要执行此操作吗？',
    })
    ElMessage.success('已确认')
  } catch {
    // 取消
  }
}

async function showDangerConfirm() {
  try {
    await confirmRef.value?.confirm({
      title: '危险操作',
      message: '确定要删除此记录吗？此操作不可恢复。',
      danger: true,
    })
    ElMessage.success('已删除')
  } catch {
    // 取消
  }
}

async function showReasonConfirm() {
  try {
    const result = await confirmRef.value?.confirm({
      title: '作废确认',
      message: '请填写作废原因',
      reasonRequired: true,
      reasonLabel: '作废原因',
    })
    ElMessage.success(`已作废，原因: ${result?.reason}`)
  } catch {
    // 取消
  }
}

// Modal 状态
const modal360 = ref(false)
const modal520 = ref(false)
const modal800 = ref(false)

// Toast 演示
function showToast(type: 'success' | 'warning' | 'error' | 'info') {
  const messages: Record<string, string> = {
    success: '操作成功',
    warning: '请注意检查',
    error: '操作失败，请稍后重试',
    info: '这是一条提示信息',
  }
  ElMessage[type](messages[type])
}
</script>

<template>
  <AppLayout>
    <div class="form-demo">
      <PageHeader title="表单演示" sub-title="FP-P-06" />

      <!-- 抽屉三档宽度 -->
      <section class="demo-section">
        <h3>FormDrawer 三档宽度</h3>
        <div class="btn-group">
          <el-button @click="drawerSizeS = true">S 宽度 (480px)</el-button>
          <el-button @click="drawerSizeM = true">M 宽度 (720px)</el-button>
          <el-button @click="drawerSizeL = true">L 宽度 (880px)</el-button>
        </div>
      </section>

      <!-- 确认框 -->
      <section class="demo-section">
        <h3>ConfirmDialog 确认框</h3>
        <div class="btn-group">
          <el-button @click="showConfirm">普通确认</el-button>
          <el-button type="danger" @click="showDangerConfirm">危险确认</el-button>
          <el-button type="warning" @click="showReasonConfirm">需填原因</el-button>
        </div>
      </section>

      <!-- Modal 三档宽度 -->
      <section class="demo-section">
        <h3>Modal 三档宽度</h3>
        <div class="btn-group">
          <el-button @click="modal360 = true">360px</el-button>
          <el-button @click="modal520 = true">520px</el-button>
          <el-button @click="modal800 = true">800px</el-button>
        </div>
      </section>

      <!-- Toast -->
      <section class="demo-section">
        <h3>Toast 消息提示</h3>
        <div class="btn-group">
          <el-button type="success" @click="showToast('success')">成功</el-button>
          <el-button type="warning" @click="showToast('warning')">警告</el-button>
          <el-button type="danger" @click="showToast('error')">错误</el-button>
          <el-button type="info" @click="showToast('info')">信息</el-button>
        </div>
      </section>

      <!-- 表单规则演示 -->
      <section class="demo-section">
        <h3>表单校验规则</h3>
        <div class="form-card">
          <el-form :model="formModel" label-width="100px">
            <el-form-item label="名称" required>
              <el-input v-model="formModel.name" placeholder="必填" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="formModel.phone" placeholder="手机号格式校验" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="formModel.email" placeholder="邮箱格式校验" />
            </el-form-item>
            <el-form-item label="金额">
              <el-input-number
                v-model="formModel.amount"
                :precision="2"
                placeholder="≤2位小数"
              />
            </el-form-item>
            <el-form-item label="百分比">
              <el-input-number
                v-model="formModel.percent"
                :min="0"
                :max="100"
                placeholder="0~100"
              />
            </el-form-item>
          </el-form>
        </div>
      </section>

      <!-- 抽屉 -->
      <FormDrawer
        v-model:open="drawerSizeS"
        title="小号抽屉"
        size="S"
        :submit="handleSubmit"
        @saved="handleSaved"
      >
        <p>这是 480px 宽的小号抽屉</p>
      </FormDrawer>

      <FormDrawer
        v-model:open="drawerSizeM"
        title="中号抽屉"
        size="M"
        :submit="handleSubmit"
        @saved="handleSaved"
      >
        <p>这是 720px 宽的中号抽屉</p>
      </FormDrawer>

      <FormDrawer
        v-model:open="drawerSizeL"
        title="大号抽屉"
        size="L"
        :submit="handleSubmit"
        @saved="handleSaved"
      >
        <p>这是 880px 宽的大号抽屉</p>
      </FormDrawer>

      <!-- 确认框组件 -->
      <ConfirmDialog ref="confirmRef" />

      <!-- Modal -->
      <el-dialog v-model="modal360" title="360px 弹窗" width="360px">
        <p>这是 360px 宽的弹窗内容</p>
      </el-dialog>

      <el-dialog v-model="modal520" title="520px 弹窗" width="520px">
        <p>这是 520px 宽的弹窗内容</p>
      </el-dialog>

      <el-dialog v-model="modal800" title="800px 弹窗" width="800px">
        <p>这是 800px 宽的弹窗内容</p>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.form-demo {
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

.btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  @include mobile {
    gap: $small-btn-gap;
  }
}

.form-card {
  padding: 20px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
}
</style>
