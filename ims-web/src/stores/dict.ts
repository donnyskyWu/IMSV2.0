/**
 * 字典 Store
 * 依据: FP-R-06 字典 Store
 * 注意: 本步只做骨架和模拟数据，真实接口接入等 B0a 契约冻结后再做
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DictItem, ColorType } from '@/types'

// 字典缓存过期时间 (10 分钟)
const CACHE_EXPIRE_MS = 10 * 60 * 1000

interface DictCache {
  items: DictItem[]
  timestamp: number
}

export const useDictStore = defineStore('dict', () => {
  const cache = ref<Map<string, DictCache>>(new Map())
  const loading = ref<Map<string, Promise<DictItem[]>>>(new Map())

  // 模拟字典数据
  const mockDicts: Record<string, DictItem[]> = {
    demo_order_status: [
      { value: 'DRAFT', label: '草稿', colorType: 'neutral' },
      { value: 'PENDING', label: '待审核', colorType: 'warning' },
      { value: 'APPROVED', label: '已通过', colorType: 'success' },
      { value: 'REJECTED', label: '已退回', colorType: 'danger' },
      { value: 'CANCELLED', label: '已取消', colorType: 'neutral' },
    ],
    user_status: [
      { value: 'ACTIVE', label: '在职', colorType: 'success' },
      { value: 'FROZEN', label: '冻结', colorType: 'warning' },
      { value: 'RESIGNED', label: '离职', colorType: 'neutral' },
    ],
    dept_source: [
      { value: 'DINGTALK', label: '钉钉', colorType: 'primary' },
      { value: 'LOCAL', label: '本地', colorType: 'info' },
    ],
    role_source: [
      { value: 'MANUAL', label: '手工', colorType: 'neutral' },
      { value: 'DINGTALK', label: '钉钉自动', colorType: 'info' },
    ],
  }

  // 获取字典列表
  async function getDict(type: string): Promise<DictItem[]> {
    // 检查缓存
    const cached = cache.value.get(type)
    if (cached && Date.now() - cached.timestamp < CACHE_EXPIRE_MS) {
      return cached.items
    }

    // 防止并发请求
    const pending = loading.value.get(type)
    if (pending) {
      return pending
    }

    // 模拟异步请求
    const promise = new Promise<DictItem[]>((resolve) => {
      setTimeout(() => {
        const items = mockDicts[type] || []
        cache.value.set(type, { items, timestamp: Date.now() })
        loading.value.delete(type)
        resolve(items)
      }, 100)
    })

    loading.value.set(type, promise)
    return promise
  }

  // 获取字典标签
  function label(type: string, value: string): string {
    const cached = cache.value.get(type)
    if (!cached) {
      // 触发加载
      getDict(type)
      return value
    }
    const item = cached.items.find((i) => i.value === value)
    if (!item) {
      console.warn(`[Dict] 未知字典值: ${type}.${value}`)
      return value
    }
    return item.label
  }

  // 获取字典颜色
  function color(type: string, value: string): ColorType | undefined {
    const cached = cache.value.get(type)
    if (!cached) {
      getDict(type)
      return undefined
    }
    const item = cached.items.find((i) => i.value === value)
    return item?.colorType
  }

  // 手动刷新
  function refresh(type: string): void {
    cache.value.delete(type)
    getDict(type)
  }

  // 刷新全部
  function refreshAll(): void {
    cache.value.clear()
  }

  return {
    getDict,
    label,
    color,
    refresh,
    refreshAll,
  }
})
