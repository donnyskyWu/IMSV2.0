/**
 * 导出下载条（跨页面保留，VC-C36）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DownloadTask {
  id: string
  name: string
  progress: number
  status: 'pending' | 'downloading' | 'completed' | 'error'
  url?: string
  reason?: string
}

export const useDownloadStore = defineStore('download', () => {
  const visible = ref(false)
  const tasks = ref<DownloadTask[]>([])

  function start(name: string) {
    visible.value = true
    tasks.value = [{ id: 'export-1', name, progress: 30, status: 'downloading' }]
  }

  function fail(reason: string) {
    visible.value = true
    tasks.value = [{
      id: 'export-1',
      name: '数据导出.xlsx',
      progress: 100,
      status: 'error',
      reason,
    }]
  }

  function hide() {
    visible.value = false
    tasks.value = []
  }

  return { visible, tasks, start, fail, hide }
})
