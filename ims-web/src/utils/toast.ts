/**
 * Toast 工具函数
 * 依据: FP-C-33
 * - 同一内容 1s 内不重复显示
 * - 最多同时显示 3 条
 */
import { ElMessage } from 'element-plus'
import type { MessageHandler, MessageOptions } from 'element-plus'

// 缓存最近的消息和时间
const recentMessages = new Map<string, number>()
const DEDUPE_INTERVAL = 1000 // 1秒去重
const MAX_VISIBLE = 3

// 当前显示的消息数
let visibleCount = 0
const pendingQueue: Array<() => void> = []

// 清理过期消息记录
function cleanupRecentMessages() {
  const now = Date.now()
  for (const [key, time] of recentMessages.entries()) {
    if (now - time > DEDUPE_INTERVAL) {
      recentMessages.delete(key)
    }
  }
}

// 生成消息 key
function getMessageKey(message: string, type: string): string {
  return `${type}:${message}`
}

// 检查是否重复
function isDuplicate(message: string, type: string): boolean {
  cleanupRecentMessages()
  const key = getMessageKey(message, type)
  const lastTime = recentMessages.get(key)
  if (lastTime && Date.now() - lastTime < DEDUPE_INTERVAL) {
    return true
  }
  recentMessages.set(key, Date.now())
  return false
}

// 处理队列
function processQueue() {
  while (pendingQueue.length > 0 && visibleCount < MAX_VISIBLE) {
    const fn = pendingQueue.shift()
    fn?.()
  }
}

// 显示消息
function showMessage(options: MessageOptions & { message: string; type: 'success' | 'warning' | 'error' | 'info' }): MessageHandler | null {
  // 去重检查
  if (isDuplicate(options.message, options.type)) {
    return null
  }

  const doShow = () => {
    visibleCount++
    const instance = ElMessage({
      ...options,
      onClose: () => {
        visibleCount--
        processQueue()
        options.onClose?.()
      },
    })
    return instance
  }

  // 超过最大数量则排队
  if (visibleCount >= MAX_VISIBLE) {
    return new Promise<void>((resolve) => {
      pendingQueue.push(() => {
        doShow()
        resolve()
      })
    }) as unknown as MessageHandler
  }

  return doShow()
}

export const toast = {
  success(message: string, options?: Partial<MessageOptions>): MessageHandler | null {
    return showMessage({ message, type: 'success', ...options })
  },

  warning(message: string, options?: Partial<MessageOptions>): MessageHandler | null {
    return showMessage({ message, type: 'warning', ...options })
  },

  error(message: string, options?: Partial<MessageOptions>): MessageHandler | null {
    return showMessage({ message, type: 'error', ...options })
  },

  info(message: string, options?: Partial<MessageOptions>): MessageHandler | null {
    return showMessage({ message, type: 'info', ...options })
  },
}

export default toast
