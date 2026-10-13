<script setup lang="ts">
/**
 * 学习中心 (FP-B21-ST-01~08)
 * 学员视图：我的学习任务列表
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import Pagination from '@/components/list/Pagination.vue'
import EmptyState from '@/components/list/EmptyState.vue'
import { toast } from '@/utils/toast'
import { getMyTasks, type TrainStudyTask } from '@/api/generated/train'
import type { EmptyType } from '@/types'

const router = useRouter()

const loading = ref(false)
const emptyMode = ref<EmptyType | ''>('')
const pageNo = ref(1)
const pageSize = ref(10)
const total = ref(0)
const tasks = ref<TrainStudyTask[]>([])

const statusFilter = ref('')

const statusOptions = [
  { label: '全部', value: '' },
  { label: '学习中', value: 'NOT_CONFIRMED' },
  { label: '已完成', value: 'CONFIRMED' },
]

async function loadTasks() {
  loading.value = true
  emptyMode.value = ''
  try {
    const res = await getMyTasks({
      status: statusFilter.value || undefined,
      pageNo: pageNo.value,
      pageSize: pageSize.value,
    })
    tasks.value = res.data?.list || []
    total.value = res.data?.total || 0
    if (tasks.value.length === 0 && !statusFilter.value) {
      emptyMode.value = 'empty'
    }
  } catch {
    emptyMode.value = 'error'
  } finally {
    loading.value = false
  }
}

function handleStudy(task: TrainStudyTask) {
  router.push(`/ims/train/study/${task.taskId}`)
}

function formatDeadline(deadline: string) {
  const d = new Date(deadline)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (diff < 0) {
    return { text: '已逾期', type: 'danger' as const }
  } else if (days === 0) {
    return { text: '今天截止', type: 'warning' as const }
  } else if (days <= 3) {
    return { text: `${days}天后截止`, type: 'warning' as const }
  }
  return { text: deadline.slice(0, 10), type: 'info' as const }
}

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${minutes}分钟`
}

onMounted(loadTasks)
watch([pageNo, pageSize, statusFilter], loadTasks)
</script>

<template>
  <AppLayout>
    <div class="study-center">
      <PageHeader title="学习中心" sub-title="我的学习任务" />

      <div class="filter-bar">
        <el-radio-group v-model="statusFilter">
          <el-radio-button v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div v-loading="loading" class="task-grid">
        <template v-if="!emptyMode && tasks.length > 0">
          <div v-for="task in tasks" :key="task.taskId" class="task-card" @click="handleStudy(task)">
            <div class="task-header">
              <h3 class="task-name">{{ task.taskName }}</h3>
              <el-tag v-if="task.confirmStatus === 'CONFIRMED'" type="success" size="small">已完成</el-tag>
              <el-tag v-else :type="formatDeadline(task.deadline).type" size="small">
                {{ formatDeadline(task.deadline).text }}
              </el-tag>
            </div>

            <div class="task-progress">
              <el-progress :percentage="task.progress" :stroke-width="8" :show-text="false" />
              <span class="progress-text">{{ task.progress }}%</span>
            </div>

            <div class="task-info">
              <div class="info-item">
                <span class="label">资料数</span>
                <span class="value">{{ task.materials.length }} 个</span>
              </div>
              <div class="info-item">
                <span class="label">已学时长</span>
                <span class="value">{{ formatDuration(task.effectiveMinutes * 60) }}</span>
              </div>
              <div v-if="task.confirmType === 'DURATION'" class="info-item">
                <span class="label">要求学时</span>
                <span class="value">{{ task.requiredMinutes }} 分钟</span>
              </div>
              <div v-if="task.confirmType === 'QUIZ'" class="info-item">
                <span class="label">确认方式</span>
                <span class="value">自测问卷</span>
              </div>
            </div>

            <div class="task-materials">
              <div v-for="material in task.materials.slice(0, 3)" :key="material.materialId" class="material-item">
                <el-icon v-if="material.materialType === 'DOC'"><Document /></el-icon>
                <el-icon v-else-if="material.materialType === 'VIDEO'"><VideoPlay /></el-icon>
                <el-icon v-else><Link /></el-icon>
                <span class="material-title">{{ material.title }}</span>
                <span v-if="material.progress === 100" class="material-done">✓</span>
              </div>
              <div v-if="task.materials.length > 3" class="material-more">
                +{{ task.materials.length - 3 }} 更多
              </div>
            </div>

            <div class="task-action">
              <el-button v-if="task.confirmStatus === 'CONFIRMED'" type="info" plain>查看</el-button>
              <el-button v-else type="primary">继续学习</el-button>
            </div>
          </div>
        </template>

        <EmptyState v-if="emptyMode" :type="emptyMode" @retry="loadTasks">
          <template v-if="emptyMode === 'empty'" #description>
            暂无学习任务
          </template>
        </EmptyState>
      </div>

      <Pagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" />
    </div>
  </AppLayout>
</template>

<style lang="scss" scoped>
.study-center {
  width: 100%;
}

.filter-bar {
  margin-bottom: 20px;
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  min-height: 200px;
}

.task-card {
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--primary);
    box-shadow: 0 4px 12px rgb(0 0 0 / 8%);
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.task-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text1);
  flex: 1;
  margin-right: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  .el-progress {
    flex: 1;
  }

  .progress-text {
    font-size: 14px;
    font-weight: 500;
    color: var(--primary);
    min-width: 40px;
  }
}

.task-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .label {
    font-size: 12px;
    color: var(--text2);
  }

  .value {
    font-size: 14px;
    color: var(--text1);
    font-weight: 500;
  }
}

.task-materials {
  margin-bottom: 16px;
}

.material-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--line);

  &:last-child {
    border-bottom: none;
  }

  .el-icon {
    color: var(--text2);
  }

  .material-title {
    flex: 1;
    font-size: 13px;
    color: var(--text1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .material-done {
    color: var(--green);
    font-weight: bold;
  }
}

.material-more {
  padding: 8px 0;
  font-size: 12px;
  color: var(--text2);
}

.task-action {
  display: flex;
  justify-content: flex-end;
}

@media (width <= 768px) {
  .task-grid {
    grid-template-columns: 1fr;
  }
}
</style>
