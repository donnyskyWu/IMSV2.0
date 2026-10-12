<script setup lang="ts">
/**
 * 表单演示页 (FP-P-05)
 * 依据: UI-L04
 * 包含: 各类表单控件、校验、提交
 */
import { ref, reactive } from 'vue'
import StepsWizard from '@/components/form/StepsWizard.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import Modal from '@/components/form/Modal.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import FormField from '@/components/form/FormField.vue'
import UserSelect from '@/components/selector/UserSelect.vue'
import DeptTreeSelect from '@/components/selector/DeptTreeSelect.vue'
import DateRangePicker from '@/components/selector/DateRangePicker.vue'
import FileUpload from '@/components/file/FileUpload.vue'
import { toast } from '@/utils/toast'
import type { DrawerSize } from '@/types'
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
const wizardOpen = ref(false)
const drawerSize = ref<DrawerSize>('M')
const drawerOpen = ref(false)
const modalTier = ref<'sm' | 'md' | 'lg'>('md')
const modalOpen = ref(false)
const voidOpen = ref(false)
const voidReason = ref('')

function openDrawer(size: DrawerSize) {
  drawerSize.value = size
  drawerOpen.value = true
}

function openModal(tier: 'sm' | 'md' | 'lg') {
  modalTier.value = tier
  modalOpen.value = true
}

function repeatToast() {
  toast.success('同一条提示')
}
const wizardStep = ref(0)
const wizardName = ref('')
const wizardError = ref('')
const wizardSteps = [
  { title: '基本信息' },
  { title: '确认' },
  { title: '完成' },
]

function wizardNext() {
  if (wizardStep.value === 0 && !wizardName.value.trim()) {
    wizardError.value = '请填写必填项'
    return
  }
  wizardError.value = ''
  wizardStep.value += 1
}

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
            <el-button @click="wizardOpen = true">打开向导</el-button>
            <div class="form-actions">
              <el-button @click="handleReset">重置</el-button>
              <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <div class="demo-launchers">
        <el-button @click="openDrawer('S')">打开小抽屉</el-button>
        <el-button @click="openDrawer('M')">打开中抽屉</el-button>
        <el-button @click="openDrawer('L')">打开大抽屉</el-button>
        <el-button @click="openModal('sm')">打开小弹窗</el-button>
        <el-button @click="openModal('md')">打开中弹窗</el-button>
        <el-button @click="openModal('lg')">打开大弹窗</el-button>
        <el-button @click="voidOpen = true">作废</el-button>
        <el-button @click="repeatToast">重复提示</el-button>
      </div>

      <FormDrawer v-model:open="drawerOpen" title="示例抽屉" :size="drawerSize">
        <el-input placeholder="抽屉内容" />
      </FormDrawer>
      <Modal v-model="modalOpen" :tier="modalTier" title="示例弹窗">
        <p>弹窗内容</p>
      </Modal>
      <el-dialog v-model="voidOpen" title="作废">
        <el-input v-model="voidReason" type="textarea" placeholder="请填写作废原因" />
        <template #footer>
          <el-button type="primary" :disabled="!voidReason.trim()">确定</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="wizardOpen" title="向导" width="640px">
        <StepsWizard :steps="wizardSteps" :current="wizardStep">
          <div v-if="wizardStep === 0">
            <el-input v-model="wizardName" placeholder="请输入名称" />
            <p v-if="wizardError" class="wizard-error">{{ wizardError }}</p>
          </div>
          <div v-else-if="wizardStep === 1">已填写：{{ wizardName }}</div>
          <div v-else>请确认提交</div>
          <template #footer>
            <el-button v-if="wizardStep > 0" @click="wizardStep -= 1">上一步</el-button>
            <el-button v-if="wizardStep < wizardSteps.length - 1" type="primary" @click="wizardNext">下一步</el-button>
            <el-button v-else type="primary">完成</el-button>
          </template>
        </StepsWizard>
      </el-dialog>
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

  @media (width <= 767px) {
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
