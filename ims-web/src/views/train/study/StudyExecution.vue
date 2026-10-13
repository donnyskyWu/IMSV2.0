<script setup lang="ts">
/**
 * 学习执行 (FP-B21-ST-02~08)
 * 学员学习页面：资料学习、进度上报、问卷作答
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { toast } from '@/utils/toast'
import {
  getStudyTaskDetail,
  reportProgress,
  saveQuizDraft,
  confirmTask,
  type TrainStudyTask,
  type TrainStudyMaterial,
  type QuizQuestion,
} from '@/api/generated/train'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const task = ref<TrainStudyTask | null>(null)
const currentMaterialIndex = ref(0)
const heartbeatTimer = ref<number | null>(null)
const lastPosition = ref(0)
const lastHeartbeatTime = ref(Date.now())

const quizMode = ref(false)
const quizAnswers = ref<Record<number, number | boolean>>({})
const quizSubmitting = ref(false)

const confirmDialogOpen = ref(false)
const confirmResult = ref<{ confirmed: boolean; score?: number; passed?: boolean } | null>(null)

const currentMaterial = computed(() => {
  if (!task.value || task.value.materials.length === 0) return null
  return task.value.materials[currentMaterialIndex.value]
})

const canConfirm = computed(() => {
  if (!task.value) return false
  if (task.value.confirmStatus === 'CONFIRMED') return false
  
  if (task.value.confirmType === 'DURATION') {
    return task.value.effectiveMinutes >= (task.value.requiredMinutes || 0)
  }
  return true
})

const allMaterialsDone = computed(() => {
  if (!task.value) return false
  return task.value.materials.every(m => m.progress === 100)
})

async function loadTask() {
  const taskId = route.params.taskId as string
  if (!taskId) {
    router.push('/ims/train/study')
    return
  }

  loading.value = true
  try {
    const res = await getStudyTaskDetail(taskId)
    task.value = res.data || null
    if (task.value && task.value.materials.length > 0) {
      const unfinished = task.value.materials.findIndex(m => m.progress < 100)
      currentMaterialIndex.value = unfinished >= 0 ? unfinished : 0
    }
  } catch (err: unknown) {
    const code = (err as { code?: number })?.code
    if (code === 1105) {
      toast.error('非被指派人')
      router.push('/ims/train/study')
    } else {
      toast.error('加载任务失败')
    }
  } finally {
    loading.value = false
  }
}

function selectMaterial(index: number) {
  if (currentMaterialIndex.value !== index) {
    stopHeartbeat()
    currentMaterialIndex.value = index
    lastPosition.value = 0
    startHeartbeat()
  }
}

function startHeartbeat() {
  if (heartbeatTimer.value) return
  lastHeartbeatTime.value = Date.now()
  
  heartbeatTimer.value = window.setInterval(async () => {
    if (!task.value || !currentMaterial.value) return
    
    const now = Date.now()
    const intervalSeconds = Math.floor((now - lastHeartbeatTime.value) / 1000)
    lastHeartbeatTime.value = now
    
    let newPosition = lastPosition.value
    if (currentMaterial.value.materialType === 'VIDEO') {
      newPosition = lastPosition.value + Math.min(intervalSeconds, 15)
    } else if (currentMaterial.value.materialType === 'DOC') {
      newPosition = lastPosition.value + 1
    } else {
      newPosition = lastPosition.value + intervalSeconds
    }
    
    try {
      const res = await reportProgress(task.value.taskId, {
        materialId: currentMaterial.value.materialId,
        position: newPosition,
        intervalSeconds,
      })
      
      if (res.data) {
        if (task.value) {
          task.value.progress = res.data.progress
          const mat = task.value.materials.find(m => m.materialId === currentMaterial.value?.materialId)
          if (mat) {
            mat.progress = Math.min(100, mat.progress + 5)
          }
        }
      }
      
      lastPosition.value = newPosition
    } catch {
      console.error('Progress report failed')
    }
  }, 15000)
}

function stopHeartbeat() {
  if (heartbeatTimer.value) {
    clearInterval(heartbeatTimer.value)
    heartbeatTimer.value = null
  }
}

function openQuizMode() {
  quizMode.value = true
  quizAnswers.value = {}
}

async function saveQuizProgress() {
  if (!task.value) return
  try {
    await saveQuizDraft(task.value.taskId, { answers: quizAnswers.value })
    toast.success('已暂存')
  } catch {
    toast.error('暂存失败')
  }
}

async function submitQuiz() {
  if (!task.value) return
  quizSubmitting.value = true
  try {
    const res = await confirmTask(task.value.taskId, { answers: quizAnswers.value })
    confirmResult.value = res.data || null
    if (res.data?.confirmed) {
      toast.success('提交成功')
      if (task.value) {
        task.value.confirmStatus = 'CONFIRMED'
      }
    }
    quizMode.value = false
    confirmDialogOpen.value = true
  } catch (err: unknown) {
    const code = (err as { code?: number })?.code
    if (code === 1104) {
      toast.error('确认条件未满足')
    } else {
      toast.error('提交失败')
    }
  } finally {
    quizSubmitting.value = false
  }
}

async function handleConfirmDuration() {
  if (!task.value) return
  try {
    const res = await confirmTask(task.value.taskId)
    confirmResult.value = res.data || null
    if (res.data?.confirmed) {
      toast.success('已确认完成')
      if (task.value) {
        task.value.confirmStatus = 'CONFIRMED'
      }
    }
    confirmDialogOpen.value = true
  } catch (err: unknown) {
    const code = (err as { code?: number })?.code
    if (code === 1104) {
      toast.error('学时未达标')
    } else {
      toast.error('确认失败')
    }
  }
}

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${minutes}分钟`
}

function goBack() {
  router.push('/ims/train/study')
}

onMounted(() => {
  loadTask()
  startHeartbeat()
})

onUnmounted(() => {
  stopHeartbeat()
})
</script>

<template>
  <AppLayout>
    <div v-loading="loading" class="study-execution">
      <PageHeader :title="task?.taskName || '学习中'" :sub-title="task?.confirmStatus === 'CONFIRMED' ? '已完成' : '学习中'">
        <template #actions>
          <el-button @click="goBack">返回列表</el-button>
          <el-button
            v-if="task?.confirmType === 'DURATION' && canConfirm"
            type="primary"
            @click="handleConfirmDuration"
          >
            确认完成
          </el-button>
          <el-button
            v-if="task?.confirmType === 'QUIZ' && !quizMode && task.confirmStatus !== 'CONFIRMED'"
            type="primary"
            @click="openQuizMode"
          >
            开始答题
          </el-button>
        </template>
      </PageHeader>

      <div v-if="!quizMode && task" class="study-content">
        <div class="study-sidebar">
          <div class="sidebar-header">
            <h4>学习资料</h4>
            <span class="progress-badge">{{ task.progress }}%</span>
          </div>
          <div class="material-list">
            <div
              v-for="(material, idx) in task.materials"
              :key="material.materialId"
              class="material-nav-item"
              :class="{ active: idx === currentMaterialIndex, done: material.progress === 100 }"
              @click="selectMaterial(idx)"
            >
              <el-icon v-if="material.materialType === 'DOC'"><Document /></el-icon>
              <el-icon v-else-if="material.materialType === 'VIDEO'"><VideoPlay /></el-icon>
              <el-icon v-else><Link /></el-icon>
              <span class="material-nav-title">{{ material.title }}</span>
              <el-icon v-if="material.progress === 100" class="done-icon"><Check /></el-icon>
            </div>
          </div>

          <div class="sidebar-stats">
            <div class="stat-item">
              <span class="stat-label">已学时长</span>
              <span class="stat-value">{{ formatDuration(task.effectiveMinutes * 60) }}</span>
            </div>
            <div v-if="task.confirmType === 'DURATION'" class="stat-item">
              <span class="stat-label">要求学时</span>
              <span class="stat-value">{{ task.requiredMinutes }} 分钟</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">截止时间</span>
              <span class="stat-value">{{ task.deadline.slice(0, 10) }}</span>
            </div>
          </div>
        </div>

        <div class="study-main">
          <div v-if="currentMaterial" class="material-viewer">
            <div class="viewer-header">
              <h3>{{ currentMaterial.title }}</h3>
              <el-progress :percentage="currentMaterial.progress" :stroke-width="6" style="width: 200px" />
            </div>

            <div class="viewer-content">
              <template v-if="currentMaterial.materialType === 'VIDEO'">
                <div class="video-placeholder">
                  <el-icon size="64"><VideoPlay /></el-icon>
                  <p>视频播放区域</p>
                  <p class="hint">时长: {{ currentMaterial.durationSeconds ? formatDuration(currentMaterial.durationSeconds) : '未知' }}</p>
                </div>
              </template>

              <template v-else-if="currentMaterial.materialType === 'DOC'">
                <div class="doc-placeholder">
                  <el-icon size="64"><Document /></el-icon>
                  <p>文档预览区域</p>
                  <p class="hint">页数: {{ currentMaterial.pageCount || '未知' }}</p>
                </div>
              </template>

              <template v-else>
                <div class="link-placeholder">
                  <el-icon size="64"><Link /></el-icon>
                  <p>外链资料</p>
                  <el-button type="primary" @click="window.open(currentMaterial.linkUrl, '_blank')">
                    打开链接
                  </el-button>
                </div>
              </template>
            </div>

            <div class="viewer-nav">
              <el-button
                :disabled="currentMaterialIndex === 0"
                @click="selectMaterial(currentMaterialIndex - 1)"
              >
                上一个
              </el-button>
              <el-button
                :disabled="currentMaterialIndex === task.materials.length - 1"
                @click="selectMaterial(currentMaterialIndex + 1)"
              >
                下一个
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="quizMode && task" class="quiz-content">
        <div class="quiz-header">
          <h3>自测问卷</h3>
          <div class="quiz-actions">
            <el-button @click="saveQuizProgress">暂存</el-button>
            <el-button @click="quizMode = false">返回学习</el-button>
            <el-button type="primary" :loading="quizSubmitting" @click="submitQuiz">提交答卷</el-button>
          </div>
        </div>

        <div class="quiz-questions">
          <div class="quiz-placeholder">
            <el-icon size="64"><Edit /></el-icon>
            <p>问卷题目区域</p>
            <p class="hint">此处显示问卷题目，学员作答后提交</p>
          </div>
        </div>
      </div>

      <el-dialog v-model="confirmDialogOpen" title="学习结果" width="400px" :close-on-click-modal="false">
        <div class="result-content">
          <template v-if="confirmResult?.confirmed">
            <el-icon class="result-icon success" size="64"><SuccessFilled /></el-icon>
            <h3>恭喜，学习完成！</h3>
            <p v-if="confirmResult.score !== undefined">得分：{{ confirmResult.score }} 分</p>
          </template>
          <template v-else>
            <el-icon class="result-icon fail" size="64"><WarningFilled /></el-icon>
            <h3>未通过</h3>
            <p v-if="confirmResult?.score !== undefined">得分：{{ confirmResult.score }} 分，未达到及格分</p>
            <p>请继续学习或重新答题</p>
          </template>
        </div>
        <template #footer>
          <el-button type="primary" @click="confirmDialogOpen = false; goBack()">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.study-execution {
  width: 100%;
  min-height: calc(100vh - 120px);
}

.study-content {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

.study-sidebar {
  width: 280px;
  flex-shrink: 0;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  padding: 16px;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);

  h4 {
    margin: 0;
    font-size: 14px;
  }

  .progress-badge {
    background-color: var(--primary);
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
  }
}

.material-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.material-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: var(--r-s);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background-color: var(--bg);
  }

  &.active {
    background-color: var(--primary-light);
    color: var(--primary);
  }

  &.done {
    .material-nav-title {
      color: var(--text2);
    }
  }

  .material-nav-title {
    flex: 1;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .done-icon {
    color: var(--green);
  }
}

.sidebar-stats {
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;

  .stat-label {
    font-size: 13px;
    color: var(--text2);
  }

  .stat-value {
    font-size: 13px;
    font-weight: 500;
    color: var(--text1);
  }
}

.study-main {
  flex: 1;
  min-width: 0;
}

.material-viewer {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  padding: 20px;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);

  h3 {
    margin: 0;
    font-size: 16px;
  }
}

.viewer-content {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg);
  border-radius: var(--r-s);
  margin-bottom: 20px;
}

.video-placeholder,
.doc-placeholder,
.link-placeholder {
  text-align: center;
  padding: 40px;
  color: var(--text2);

  .el-icon {
    margin-bottom: 16px;
    color: var(--text3);
  }

  p {
    margin: 8px 0;
  }

  .hint {
    font-size: 13px;
    color: var(--text3);
  }
}

.viewer-nav {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.quiz-content {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  padding: 20px;
  margin-top: 20px;
}

.quiz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);

  h3 {
    margin: 0;
  }
}

.quiz-actions {
  display: flex;
  gap: 8px;
}

.quiz-questions {
  min-height: 400px;
}

.quiz-placeholder {
  text-align: center;
  padding: 80px 40px;
  color: var(--text2);

  .el-icon {
    margin-bottom: 16px;
    color: var(--text3);
  }

  .hint {
    font-size: 13px;
    color: var(--text3);
    margin-top: 8px;
  }
}

.result-content {
  text-align: center;
  padding: 20px;

  .result-icon {
    margin-bottom: 16px;

    &.success {
      color: var(--green);
    }

    &.fail {
      color: var(--orange);
    }
  }

  h3 {
    margin: 0 0 12px;
  }

  p {
    margin: 8px 0;
    color: var(--text2);
  }
}

@media (max-width: 768px) {
  .study-content {
    flex-direction: column;
  }

  .study-sidebar {
    width: 100%;
  }
}
</style>
