<script setup lang="ts">
/**
 * DownloadBar 下载进度条
 * 依据: FP-C18-03
 * 显示下载任务进度
 */
import { ref, computed, watch } from 'vue'
import { Download, Close, CircleCheckFilled } from '@element-plus/icons-vue'

interface DownloadTask {
  id: string
  name: string
  progress: number
  status: 'pending' | 'downloading' | 'completed' | 'error'
  url?: string
}

interface Props {
  tasks: DownloadTask[]
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: true,
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'cancel', taskId: string): void
  (e: 'download', task: DownloadTask): void
}>()

// 当前任务
const currentTask = computed(() => {
  return props.tasks.find((t) => t.status === 'downloading')
})

// 是否有进行中的任务
const hasActiveTask = computed(() => {
  return props.tasks.some((t) => t.status === 'pending' || t.status === 'downloading')
})

// 已完成的任务数
const completedCount = computed(() => {
  return props.tasks.filter((t) => t.status === 'completed').length
})

// 下载完成的文件
function handleDownload(task: DownloadTask) {
  if (task.url) {
    const link = document.createElement('a')
    link.href = task.url
    link.download = task.name
    link.click()
  }
  emit('download', task)
}
</script>

<template>
  <Transition name="slide-up">
    <div v-if="visible && tasks.length > 0" class="download-bar">
      <div class="bar-header">
        <div class="bar-title">
          <el-icon><Download /></el-icon>
          <span v-if="hasActiveTask">正在下载...</span>
          <span v-else>下载完成</span>
        </div>
        <el-button text size="small" @click="emit('close')">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <div class="bar-content">
        <!-- 当前下载任务 -->
        <div v-if="currentTask" class="current-task">
          <div class="task-name">{{ currentTask.name }}</div>
          <el-progress
            :percentage="currentTask.progress"
            :stroke-width="4"
            :show-text="false"
          />
        </div>

        <!-- 已完成的任务 -->
        <div v-if="completedCount > 0" class="completed-tasks">
          <div
            v-for="task in tasks.filter((t) => t.status === 'completed')"
            :key="task.id"
            class="task-item"
            @click="handleDownload(task)"
          >
            <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
            <span class="task-name">{{ task.name }}</span>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style lang="scss" scoped>
.download-bar {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 320px;
  background-color: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-m);
  box-shadow: 0 4px 12px rgb(0 0 0 / 10%);
  z-index: 2000;
  overflow: hidden;
}

.bar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);

  .bar-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
  }
}

.bar-content {
  padding: 12px 16px;
  max-height: 200px;
  overflow-y: auto;
}

.current-task {
  margin-bottom: 12px;

  .task-name {
    font-size: 13px;
    color: var(--text2);
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.completed-tasks {
  .task-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    margin: -8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;

    &:hover {
      background-color: var(--hover);
    }

    .success-icon {
      color: var(--green);
    }

    .task-name {
      font-size: 13px;
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

// 动画
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
