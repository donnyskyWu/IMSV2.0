<script setup lang="ts">
/**
 * 表单演示页 (FP-P-05)
 * 依据: UI-L04
 * 包含: 各类表单控件、校验、提交
 */
import { ref, reactive } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import FormField from '@/components/form/FormField.vue'
import UserSelect from '@/components/selector/UserSelect.vue'
import DeptTreeSelect from '@/components/selector/DeptTreeSelect.vue'
import DateRangePicker from '@/components/selector/DateRangePicker.vue'
import FileUpload from '@/components/file/FileUpload.vue'
import { toast } from '@/utils/toast'
import type { FormInstance, FormRules } from 'element-plus'

// 表单引用
const formRef = ref<FormInstance>()

// 表单数据
const formModel = reactive({
  name: '',
  email: '',
  phone: '',
  deptId: undefined as number | undefined,
  userId: undefined as number | undefined,
  status: 'ACTIVE',
  dateRange: null as [string, string] | null,
  remark: '',
  files: [] as string[],
  agreement: false,
})

// 校验规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度在 2-20 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  deptId: [{ required: true, message: '请选择部门', trigger: 'change' }],
  agreement: [
    {
      validator: (_rule, value, callback) => {
        if (!value) {
          callback(new Error('请阅读并同意服务协议'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
}

// 提交状态
const submitting = ref(false)

// 提交表单
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    toast.warning('请检查表单填写')
    return
  }

  submitting.value = true
  try {
    // 模拟提交
    await new Promise((r) => setTimeout(r, 1500))
    console.log('Form submitted:', formModel)
    toast.success('提交成功')
  } finally {
    submitting.value = false
  }
}

// 重置表单
function handleReset() {
  formRef.value?.resetFields()
}
</script>

<template>
  <AppLayout>
    <div class="form-demo">
      <PageHeader title="表单演示" sub-title="FP-P-05 / UI-L04" />

      <div class="form-container">
        <el-form
          ref="formRef"
          :model="formModel"
          :rules="formRules"
          label-width="100px"
          label-position="right"
        >
          <h3 class="form-section-title">基本信息</h3>

          <el-form-item label="姓名" prop="name">
            <el-input v-model="formModel.name" placeholder="请输入姓名" maxlength="20" show-word-limit />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input v-model="formModel.email" placeholder="请输入邮箱" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone">
            <el-input v-model="formModel.phone" placeholder="请输入手机号" maxlength="11" />
          </el-form-item>

          <el-form-item label="所属部门" prop="deptId">
            <DeptTreeSelect v-model="formModel.deptId" />
          </el-form-item>

          <el-form-item label="负责人">
            <UserSelect v-model="formModel.userId" placeholder="选择负责人" />
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="formModel.status">
              <el-radio value="ACTIVE">启用</el-radio>
              <el-radio value="DISABLED">禁用</el-radio>
            </el-radio-group>
          </el-form-item>

          <h3 class="form-section-title">其他信息</h3>

          <el-form-item label="有效期">
            <DateRangePicker v-model="formModel.dateRange" />
          </el-form-item>

          <el-form-item label="备注">
            <el-input
              v-model="formModel.remark"
              type="textarea"
              :rows="3"
              placeholder="请输入备注信息"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="附件">
            <FileUpload
              v-model="formModel.files"
              :max-count="3"
              :max-size="5"
              tip="支持上传 3 个文件，单个不超过 5MB"
            />
          </el-form-item>

          <el-form-item prop="agreement">
            <el-checkbox v-model="formModel.agreement">
              我已阅读并同意
              <el-link type="primary" :underline="false">《服务协议》</el-link>
            </el-checkbox>
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <el-button @click="handleReset">重置</el-button>
              <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.form-demo {
  max-width: 800px;
}

.form-container {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 24px;

  @media (max-width: 767px) {
    padding: 16px;
  }
}

.form-section-title {
  margin: 0 0 20px;
  padding-bottom: 12px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
  border-bottom: 1px solid var(--line);

  &:not(:first-child) {
    margin-top: 24px;
  }
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}
</style>
