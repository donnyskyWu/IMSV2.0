<script setup lang="ts">
/**
 * 学习任务 (FP-B21-TK-01~11)
 * 任务列表页：按数据范围展示任务
 */
import { ref, computed, watch, onMounted } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Pagination from '@/components/list/Pagination.vue'
import StatusTag from '@/components/list/StatusTag.vue'
import FormDrawer from '@/components/form/FormDrawer.vue'
import DetailDrawer from '@/components/form/DetailDrawer.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { toast } from '@/utils/toast'
import { useDictStore } from '@/stores/dict'
import { useResponsive } from '@/utils/responsive'
import {
  getTaskList,
  getTaskDetail,
  createTask,
  updateTask,
  deleteTask,
  getTaskRecords,
  previewPositionUsers,
  generateQuizByAI,
  type TrainTask,
  type TrainTaskDetail,
  type TrainTaskRecord,
  type QuizQuestion,
} from '@/api/generated/train'
import type { EmptyType } from '@/types'

const dictStore = useDictStore()
const { isMobile } = useResponsive()

const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')
const pageNo = ref(1)
const pageSize = ref(10)
const total = ref(0)
const tasks = ref<TrainTask[]>([])

const searchForm = ref({
  keyword: '',
  status: '',
  confirmType: '',
})

const createDrawerOpen = ref(false)
const createStep = ref(1)
const taskForm = ref({
  taskName: '',
  materialIds: [] as string[],
  assignScope: 'BY_USER' as 'BY_USER' | 'BY_POSITION',
  assignedUserIds: [] as string[],
  assignedPositionCodes: [] as string[],
  deadline: '',
  confirmType: 'DURATION' as 'DURATION' | 'QUIZ',
  requiredMinutes: 60,
  quiz: [] as QuizQuestion[],
  passScore: 60,
})
const isEdit = ref(false)
const editingId = ref('')

const detailDrawerOpen = ref(false)
const detailTab = ref('base')
const detailData = ref<TrainTaskDetail | null>(null)

const recordsDrawerOpen = ref(false)
const recordsLoading = ref(false)
const records = ref<TrainTaskRecord[]>([])
const recordsTotal = ref(0)
const recordsPageNo = ref(1)
const recordsPageSize = ref(10)
const currentTaskId = ref('')

const aiWizardOpen = ref(false)
const aiWizardStep = ref(1)
const aiLoading = ref(false)
const aiError = ref('')
const aiQuestions = ref<QuizQuestion[]>([])

const confirmDeleteOpen = ref(false)
const pendingDeleteTask = ref<TrainTask | null>(null)

const previewCount = ref(0)

async function loadTasks() {
  loading.value = true
  emptyMode.value = ''
  try {
    const res = await getTaskList({
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      ...searchForm.value,
    })
    tasks.value = res.data?.list || []
    total.value = res.data?.total || 0
    if (tasks.value.length === 0 && !searchForm.value.keyword && !searchForm.value.status) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pageNo.value = 1
  loadTasks()
}

function handleReset() {
  searchForm.value = { keyword: '', status: '', confirmType: '' }
  handleSearch()
}

function handleCreate() {
  isEdit.value = false
  editingId.value = ''
  createStep.value = 1
  taskForm.value = {
    taskName: '',
    materialIds: [],
    assignScope: 'BY_USER',
    assignedUserIds: [],
    assignedPositionCodes: [],
    deadline: '',
    confirmType: 'DURATION',
    requiredMinutes: 60,
    quiz: [],
    passScore: 60,
  }
  createDrawerOpen.value = true
}

async function handleEdit(row: TrainTask) {
  isEdit.value = true
  editingId.value = row.id
  try {
    const res = await getTaskDetail(row.id)
    const detail = res.data
    if (detail) {
      taskForm.value = {
        taskName: detail.taskName,
        materialIds: detail.materialIds,
        assignScope: detail.assignScope,
        assignedUserIds: [],
        assignedPositionCodes: [],
        deadline: detail.deadline,
        confirmType: detail.confirmType,
        requiredMinutes: detail.requiredMinutes || 60,
        quiz: detail.quiz || [],
        passScore: detail.passScore || 60,
      }
      createStep.value = 1
      createDrawerOpen.value = true
    }
  } catch {
    toast.error('加载任务失败')
  }
}

async function handleView(row: TrainTask) {
  try {
    const res = await getTaskDetail(row.id)
    detailData.value = res.data || null
    detailTab.value = 'base'
    detailDrawerOpen.value = true
  } catch {
    toast.error('加载详情失败')
  }
}

async function handleViewRecords(row: TrainTask) {
  currentTaskId.value = row.id
  recordsPageNo.value = 1
  recordsDrawerOpen.value = true
  await loadRecords()
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const res = await getTaskRecords({
      taskId: currentTaskId.value,
      pageNo: recordsPageNo.value,
      pageSize: recordsPageSize.value,
    })
    records.value = res.data?.list || []
    recordsTotal.value = res.data?.total || 0
  } catch {
    toast.error('加载记录失败')
  } finally {
    recordsLoading.value = false
  }
}

async function handleSubmitTask() {
  const data = {
    taskName: taskForm.value.taskName,
    materialIds: taskForm.value.materialIds,
    assignScope: taskForm.value.assignScope,
    assignedUserIds: taskForm.value.assignScope === 'BY_USER' ? taskForm.value.assignedUserIds : undefined,
    assignedPositionCodes: taskForm.value.assignScope === 'BY_POSITION' ? taskForm.value.assignedPositionCodes : undefined,
    deadline: taskForm.value.deadline,
    confirmType: taskForm.value.confirmType,
    requiredMinutes: taskForm.value.confirmType === 'DURATION' ? taskForm.value.requiredMinutes : undefined,
    quiz: taskForm.value.confirmType === 'QUIZ' ? taskForm.value.quiz : undefined,
    passScore: taskForm.value.confirmType === 'QUIZ' ? taskForm.value.passScore : undefined,
    clientToken: window.crypto.randomUUID(),
  }

  if (isEdit.value) {
    await updateTask(editingId.value, {
      taskName: data.taskName,
      materialIds: data.materialIds,
      deadline: data.deadline,
      requiredMinutes: data.requiredMinutes,
    })
    toast.success('更新成功')
  } else {
    await createTask(data)
    toast.success('创建成功')
  }
  createDrawerOpen.value = false
  loadTasks()
}

function handleDelete(row: TrainTask) {
  pendingDeleteTask.value = row
  confirmDeleteOpen.value = true
}

async function confirmDelete() {
  if (!pendingDeleteTask.value) return
  try {
    await deleteTask(pendingDeleteTask.value.id)
    toast.success('已删除')
    confirmDeleteOpen.value = false
    loadTasks()
  } catch {
    toast.error('删除失败')
  }
}

async function handlePreviewPosition() {
  if (taskForm.value.assignedPositionCodes.length === 0) {
    previewCount.value = 0
    return
  }
  try {
    const res = await previewPositionUsers(taskForm.value.assignedPositionCodes)
    previewCount.value = res.data?.count || 0
  } catch {
    previewCount.value = 0
  }
}

function openAIWizard() {
  aiWizardStep.value = 1
  aiError.value = ''
  aiQuestions.value = []
  aiWizardOpen.value = true
}

async function generateAIQuiz() {
  if (taskForm.value.materialIds.length === 0) {
    aiError.value = '请先选择学习资料'
    return
  }
  aiLoading.value = true
  aiError.value = ''
  try {
    const res = await generateQuizByAI({ materialIds: taskForm.value.materialIds })
    aiQuestions.value = res.data?.questions || []
    if (aiQuestions.value.length === 0) {
      aiError.value = '生成的题目数量为0，请重试'
    } else {
      aiWizardStep.value = 3
    }
  } catch (err: unknown) {
    const code = (err as { code?: number })?.code
    if (code === 1106) {
      aiError.value = '培训AI调用失败，请重试'
    } else if (code === 1107) {
      aiError.value = '生成超时，请稍后再试'
    } else if (code === 1109) {
      aiError.value = '培训AI未配置，请联系管理员'
    } else {
      aiError.value = '生成失败，请重试'
    }
  } finally {
    aiLoading.value = false
  }
}

function applyAIQuiz() {
  taskForm.value.quiz = [...aiQuestions.value]
  aiWizardOpen.value = false
  toast.success('已应用AI生成的试卷')
}

const statusOptions = [
  { label: '进行中', value: 'IN_PROGRESS' },
  { label: '已结束', value: 'FINISHED' },
]

const confirmTypeOptions = [
  { label: '学时达标', value: 'DURATION' },
  { label: '自测问卷', value: 'QUIZ' },
]

onMounted(() => {
  dictStore.applyLocal('dict_train_task_status', [
    { dictValue: 'IN_PROGRESS', dictLabel: '进行中', colorType: 'success' },
    { dictValue: 'FINISHED', dictLabel: '已结束', colorType: 'neutral' },
  ])
  dictStore.applyLocal('dict_train_confirm_type', [
    { dictValue: 'DURATION', dictLabel: '学时达标', colorType: 'purple' },
    { dictValue: 'QUIZ', dictLabel: '自测问卷', colorType: 'success' },
  ])
  loadTasks()
})

watch([pageNo, pageSize], loadTasks)
watch(recordsPageNo, loadRecords)
watch(() => taskForm.value.assignedPositionCodes, handlePreviewPosition)
</script>

<template>
  <AppLayout>
    <div class="task-list">
      <PageHeader title="学习任务" sub-title="FP-B21-TK">
        <template #actions>
          <el-button v-perm="'ims:train:task:add'" type="primary" @click="handleCreate">创建任务</el-button>
        </template>
        <template #primary-action>
          <el-button v-perm="'ims:train:task:add'" type="primary" @click="handleCreate">创建</el-button>
        </template>
      </PageHeader>

      <div class="query-bar">
        <el-form :model="searchForm" inline @submit.prevent="handleSearch">
          <el-form-item label="关键词">
            <el-input v-model="searchForm.keyword" placeholder="任务名称" clearable style="width: 160px" @keyup.enter="handleSearch" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 100px">
              <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="确认方式">
            <el-select v-model="searchForm.confirmType" placeholder="全部" clearable style="width: 100px">
              <el-option v-for="opt in confirmTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-loading="loading" class="table-wrap">
        <el-table v-if="!emptyMode" :data="tasks" style="width: 100%">
          <el-table-column prop="taskName" label="任务名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="taskNo" label="编号" width="140">
            <template #default="{ row }">
              <span class="mono">{{ row.taskNo }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <StatusTag dict-type="dict_train_task_status" :value="row.status" />
            </template>
          </el-table-column>
          <el-table-column prop="confirmType" label="确认方式" width="100">
            <template #default="{ row }">
              <StatusTag dict-type="dict_train_confirm_type" :value="row.confirmType" />
            </template>
          </el-table-column>
          <el-table-column label="完成率" width="100">
            <template #default="{ row }">
              {{ row.assignedCount > 0 ? Math.round(row.finishedCount / row.assignedCount * 100) : 0 }}%
            </template>
          </el-table-column>
          <el-table-column prop="deadline" label="截止时间" width="160" />
          <el-table-column prop="createTime" label="创建时间" width="160" />
          <el-table-column label="操作" :width="isMobile ? 72 : 220" fixed="right">
            <template #default="{ row }">
              <el-button v-if="!isMobile" v-perm="'ims:train:task:query'" text type="primary" size="small" @click="handleView(row)">查看</el-button>
              <el-button v-if="!isMobile" v-perm="'ims:train:task:query'" text type="primary" size="small" @click="handleViewRecords(row)">记录</el-button>
              <el-button v-if="!isMobile && row.status === 'IN_PROGRESS'" v-perm="'ims:train:task:edit'" text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-dropdown trigger="click">
                <el-button text type="primary" size="small">更多</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="isMobile" @click="handleView(row)">查看</el-dropdown-item>
                    <el-dropdown-item v-if="isMobile" @click="handleViewRecords(row)">记录</el-dropdown-item>
                    <el-dropdown-item v-if="isMobile && row.status === 'IN_PROGRESS'" @click="handleEdit(row)">编辑</el-dropdown-item>
                    <el-dropdown-item v-perm="'ims:train:task:delete'" divided @click="handleDelete(row)">
                      <span class="danger-text">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
        <EmptyState v-else :type="emptyMode" @retry="loadTasks" />
      </div>

      <Pagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" />

      <!-- Create/Edit Drawer -->
      <FormDrawer
        v-model:open="createDrawerOpen"
        :title="isEdit ? '编辑任务' : '创建任务'"
        size="L"
        :submit="handleSubmitTask"
      >
        <el-steps :active="createStep" simple style="margin-bottom: 24px">
          <el-step title="基本信息" />
          <el-step title="指派学员" />
          <el-step title="确认方式" />
        </el-steps>

        <el-form v-show="createStep === 1" :model="taskForm" label-width="100px">
          <el-form-item label="任务名称" required>
            <el-input v-model="taskForm.taskName" placeholder="请输入任务名称（最多128字）" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="截止时间" required>
            <el-date-picker v-model="taskForm.deadline" type="datetime" placeholder="选择截止时间" style="width: 100%" />
          </el-form-item>
          <el-form-item label="学习资料" required>
            <el-select v-model="taskForm.materialIds" multiple placeholder="选择资料" style="width: 100%">
              <el-option label="示例资料1" value="1" />
              <el-option label="示例资料2" value="2" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-form v-show="createStep === 2" :model="taskForm" label-width="100px">
          <el-form-item label="指派方式" required>
            <el-radio-group v-model="taskForm.assignScope" :disabled="isEdit">
              <el-radio value="BY_USER">按人指派</el-radio>
              <el-radio value="BY_POSITION">按岗位指派</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="taskForm.assignScope === 'BY_USER'" label="指派学员" required>
            <el-select v-model="taskForm.assignedUserIds" multiple placeholder="选择学员" style="width: 100%" :disabled="isEdit">
              <el-option label="张三" value="1" />
              <el-option label="李四" value="2" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="taskForm.assignScope === 'BY_POSITION'" label="指派岗位" required>
            <el-select v-model="taskForm.assignedPositionCodes" multiple placeholder="选择岗位" style="width: 100%" :disabled="isEdit">
              <el-option label="主播组" value="B21_ANCHOR" />
              <el-option label="直播运营" value="B21_OPERATOR" />
            </el-select>
            <div v-if="previewCount > 0" class="preview-hint">将指派给 {{ previewCount }} 人</div>
          </el-form-item>
        </el-form>

        <el-form v-show="createStep === 3" :model="taskForm" label-width="100px">
          <el-form-item label="确认方式" required>
            <el-radio-group v-model="taskForm.confirmType" :disabled="isEdit">
              <el-radio value="DURATION">学时达标</el-radio>
              <el-radio value="QUIZ">自测问卷</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="taskForm.confirmType === 'DURATION'" label="要求学时">
            <el-input-number v-model="taskForm.requiredMinutes" :min="1" :max="999" /> 分钟
          </el-form-item>
          <el-form-item v-if="taskForm.confirmType === 'QUIZ'" label="及格分">
            <el-input-number v-model="taskForm.passScore" :min="1" :max="100" /> 分
          </el-form-item>
          <el-form-item v-if="taskForm.confirmType === 'QUIZ'" label="试卷题目">
            <div class="quiz-actions">
              <el-button v-perm="'ims:train:quiz:ai'" type="primary" @click="openAIWizard">AI生成</el-button>
              <el-button>手动添加</el-button>
            </div>
            <div v-if="taskForm.quiz.length > 0" class="quiz-preview">
              已配置 {{ taskForm.quiz.length }} 道题目
            </div>
          </el-form-item>
        </el-form>

        <div class="step-actions">
          <el-button v-if="createStep > 1" @click="createStep--">上一步</el-button>
          <el-button v-if="createStep < 3" type="primary" @click="createStep++">下一步</el-button>
        </div>
      </FormDrawer>

      <!-- Detail Drawer -->
      <DetailDrawer
        v-model="detailDrawerOpen"
        :title="detailData?.taskName || '任务详情'"
        :tabs="[{ key: 'base', label: '基本信息' }, { key: 'materials', label: '学习资料' }]"
        :active-tab="detailTab"
        @update:active-tab="detailTab = $event"
      >
        <template v-if="detailTab === 'base'">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="编号">{{ detailData?.taskNo }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <StatusTag dict-type="dict_train_task_status" :value="detailData?.status || ''" />
            </el-descriptions-item>
            <el-descriptions-item label="确认方式">
              <StatusTag dict-type="dict_train_confirm_type" :value="detailData?.confirmType || ''" />
            </el-descriptions-item>
            <el-descriptions-item label="截止时间">{{ detailData?.deadline }}</el-descriptions-item>
            <el-descriptions-item label="指派人数">{{ detailData?.assignedCount }}</el-descriptions-item>
            <el-descriptions-item label="完成人数">{{ detailData?.finishedCount }}</el-descriptions-item>
            <el-descriptions-item v-if="detailData?.confirmType === 'DURATION'" label="要求学时">{{ detailData?.requiredMinutes }} 分钟</el-descriptions-item>
            <el-descriptions-item v-if="detailData?.confirmType === 'QUIZ'" label="及格分">{{ detailData?.passScore }} 分</el-descriptions-item>
          </el-descriptions>
        </template>
        <template v-if="detailTab === 'materials'">
          <el-table :data="detailData?.materials || []" style="width: 100%">
            <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />
            <el-table-column prop="materialType" label="类型" width="80">
              <template #default="{ row }">
                <StatusTag dict-type="dict_train_material_type" :value="row.materialType" />
              </template>
            </el-table-column>
          </el-table>
        </template>
        <template #footer>
          <el-button @click="detailDrawerOpen = false">关闭</el-button>
        </template>
      </DetailDrawer>

      <!-- Records Drawer -->
      <FormDrawer v-model:open="recordsDrawerOpen" title="学习记录" size="L" :show-footer="false">
        <div v-loading="recordsLoading">
          <el-table :data="records" style="width: 100%">
            <el-table-column prop="userName" label="学员" width="100" />
            <el-table-column prop="userDeptName" label="部门" width="120" />
            <el-table-column label="进度" width="100">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :stroke-width="6" />
              </template>
            </el-table-column>
            <el-table-column label="有效学时" width="100">
              <template #default="{ row }">
                {{ Math.floor(row.effectiveSeconds / 60) }}分钟
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.confirmStatus === 'CONFIRMED'" type="success">已完成</el-tag>
                <el-tag v-else-if="row.isOverdue" type="danger">逾期</el-tag>
                <el-tag v-else type="info">学习中</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="finishedAt" label="完成时间" width="160">
              <template #default="{ row }">
                {{ row.finishedAt || '-' }}
              </template>
            </el-table-column>
          </el-table>
          <Pagination v-model:page-no="recordsPageNo" v-model:page-size="recordsPageSize" :total="recordsTotal" />
        </div>
      </FormDrawer>

      <!-- AI Wizard Dialog -->
      <el-dialog v-model="aiWizardOpen" title="AI生成试卷" width="600px" :close-on-click-modal="false">
        <el-steps :active="aiWizardStep" simple style="margin-bottom: 24px">
          <el-step title="选择资料" />
          <el-step title="生成中" />
          <el-step title="预览题目" />
          <el-step title="应用" />
        </el-steps>

        <div v-if="aiWizardStep === 1">
          <p>将基于已选择的 {{ taskForm.materialIds.length }} 个资料生成试卷</p>
          <el-alert v-if="taskForm.materialIds.length === 0" type="warning" :closable="false">
            请先在上一步选择学习资料
          </el-alert>
        </div>

        <div v-if="aiWizardStep === 2">
          <div v-if="aiLoading" class="ai-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>AI 正在生成试卷，请稍候...</p>
          </div>
          <el-alert v-if="aiError" type="error" :closable="false">
            {{ aiError }}
            <el-button type="primary" size="small" style="margin-left: 12px" @click="generateAIQuiz">重试</el-button>
          </el-alert>
        </div>

        <div v-if="aiWizardStep === 3">
          <p>已生成 {{ aiQuestions.length }} 道题目：</p>
          <div v-for="(q, idx) in aiQuestions" :key="idx" class="quiz-item">
            <p><strong>{{ idx + 1 }}. {{ q.question }}</strong></p>
            <ul v-if="q.options">
              <li v-for="(opt, i) in q.options" :key="i">{{ String.fromCharCode(65 + i) }}. {{ opt }}</li>
            </ul>
          </div>
        </div>

        <template #footer>
          <el-button @click="aiWizardOpen = false">取消</el-button>
          <el-button v-if="aiWizardStep === 1" type="primary" :disabled="taskForm.materialIds.length === 0" @click="aiWizardStep = 2; generateAIQuiz()">开始生成</el-button>
          <el-button v-if="aiWizardStep === 3" type="primary" @click="applyAIQuiz">应用到任务</el-button>
        </template>
      </el-dialog>

      <!-- Confirm Delete Dialog -->
      <el-dialog v-model="confirmDeleteOpen" title="确认删除" width="420px" :close-on-click-modal="false">
        <p>确定删除任务「{{ pendingDeleteTask?.taskName }}」？</p>
        <p class="hint-text">删除后学员的学习记录将被清除</p>
        <template #footer>
          <el-button @click="confirmDeleteOpen = false">取消</el-button>
          <el-button type="danger" @click="confirmDelete">确定删除</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.task-list {
  width: 100%;
}

.query-bar {
  margin-bottom: 16px;
  padding: 16px;
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);

  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }
}

.table-wrap {
  background-color: var(--card);
  border-radius: var(--r-s);
  border: 1px solid var(--line);
  overflow: hidden;
  min-height: 200px;
}

.mono {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
}

.danger-text {
  color: var(--red);
}

.hint-text {
  color: var(--text2);
  font-size: 13px;
  margin-top: 8px;
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.preview-hint {
  margin-top: 8px;
  color: var(--primary);
  font-size: 13px;
}

.quiz-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.quiz-preview {
  color: var(--text2);
  font-size: 13px;
}

.ai-loading {
  text-align: center;
  padding: 40px;

  .el-icon {
    font-size: 32px;
    color: var(--primary);
    margin-bottom: 12px;
  }
}

.quiz-item {
  padding: 12px;
  margin-bottom: 8px;
  background-color: var(--bg);
  border-radius: var(--r-s);

  ul {
    margin: 8px 0 0 16px;
    padding: 0;
    list-style: none;
  }
}
</style>
