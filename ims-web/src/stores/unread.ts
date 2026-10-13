/**
 * 未读消息数 Store（B3 新建）
 * 依据: 个人工作台-实现理解 §7.3
 *
 * 功能:
 * - 存储未读消息数
 * - 60 秒轮询刷新
 * - AppLayout 挂载时启动轮询
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { messageApi } from '@/api/workbench'
import { getAccessToken } from '@/api/request'

const POLL_INTERVAL = 60000 // 60 秒

export const useUnreadStore = defineStore('unread', () => {
  const count = ref(0)
  const lastFetch = ref(0)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetch() {
    if (!getAccessToken()) {
      count.value = 0
      return
    }

    try {
      const res = await messageApi.getUnreadCount()
      if (res.code === 0 && res.data !== null) {
        count.value = res.data
        lastFetch.value = Date.now()
      }
    } catch {
      // 静默失败，不影响页面
    }
  }

  function decrement() {
    count.value = Math.max(0, count.value - 1)
  }

  function increment() {
    count.value += 1
  }

  function reset() {
    count.value = 0
    lastFetch.value = 0
  }

  function startPolling() {
    stopPolling()
    fetch()
    pollTimer = setInterval(fetch, POLL_INTERVAL)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    count,
    lastFetch,
    fetch,
    decrement,
    increment,
    reset,
    startPolling,
    stopPolling,
  }
})
