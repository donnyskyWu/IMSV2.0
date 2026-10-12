/**
 * 字典 Store
 * 依据: FP-R-06, B0a 工作包 §5 (FW-B07)
 *
 * 功能:
 * - 字典类型列表加载
 * - 字典值列表加载
 * - 本地缓存 (10 分钟过期)
 * - 并发请求合并
 * - 手动刷新
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dictApi } from '@/api/generated'
import type { DictItem, ColorType } from '@/types'

const CACHE_EXPIRE_MS = 10 * 60 * 1000

interface DictCache {
  items: DictItem[]
  timestamp: number
}

const COLOR_MAP: Record<string, ColorType> = {
  primary: 'primary',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  info: 'info',
  default: 'neutral',
}

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
  ticket_priority: [
    { value: 'LOW', label: '低', colorType: 'neutral' },
    { value: 'MEDIUM', label: '中', colorType: 'info' },
    { value: 'HIGH', label: '高', colorType: 'warning' },
    { value: 'URGENT', label: '紧急', colorType: 'danger' },
  ],
  ticket_status: [
    { value: 'pending', label: '待处理', colorType: 'warning' },
    { value: 'processing', label: '处理中', colorType: 'primary' },
    { value: 'completed', label: '已完成', colorType: 'success' },
    { value: 'closed', label: '已关闭', colorType: 'neutral' },
  ],
  product_status: [
    { value: 'ON_SALE', label: '在售', colorType: 'success' },
    { value: 'OFF_SALE', label: '下架', colorType: 'neutral' },
    { value: 'SOLD_OUT', label: '售罄', colorType: 'warning' },
  ],
}

export const useDictStore = defineStore('dict', () => {
  const cache = ref<Map<string, DictCache>>(new Map())
  const loading = ref<Map<string, Promise<DictItem[]>>>(new Map())
  const useMock = ref(import.meta.env.DEV || import.meta.env.MODE === 'test')

  async function fetchDictFromApi(type: string): Promise<DictItem[]> {
    try {
      const result = await dictApi.getDataList({ dictType: type })
      if (result.code === 0 && result.data) {
        return result.data.map((item) => ({
          value: item.value || '',
          label: item.label || '',
          colorType: COLOR_MAP[item.colorType || 'default'] || 'neutral',
          disabled: item.status === 0,
        }))
      }
      return []
    } catch {
      return mockDicts[type] || []
    }
  }

  async function getDict(type: string): Promise<DictItem[]> {
    const cached = cache.value.get(type)
    if (cached && Date.now() - cached.timestamp < CACHE_EXPIRE_MS) {
      return cached.items
    }

    const pending = loading.value.get(type)
    if (pending) {
      return pending
    }

    let promise: Promise<DictItem[]>

    if (useMock.value && mockDicts[type]) {
      promise = new Promise<DictItem[]>((resolve) => {
        setTimeout(() => {
          const items = mockDicts[type] || []
          cache.value.set(type, { items, timestamp: Date.now() })
          loading.value.delete(type)
          resolve(items)
        }, 50)
      })
    } else {
      promise = fetchDictFromApi(type).then((items) => {
        cache.value.set(type, { items, timestamp: Date.now() })
        loading.value.delete(type)
        return items
      })
    }

    loading.value.set(type, promise)
    return promise
  }

  function label(type: string, value: string): string {
    const cached = cache.value.get(type)
    if (!cached) {
      getDict(type)
      return value
    }
    const item = cached.items.find((i) => i.value === value)
    if (!item) {
      return value
    }
    return item.label
  }

  function color(type: string, value: string): ColorType | undefined {
    const cached = cache.value.get(type)
    if (!cached) {
      getDict(type)
      return undefined
    }
    const item = cached.items.find((i) => i.value === value)
    return item?.colorType
  }

  function refresh(type: string): void {
    cache.value.delete(type)
    getDict(type)
  }

  function refreshAll(): void {
    cache.value.clear()
  }

  return {
    getDict,
    label,
    color,
    refresh,
    refreshAll,
    useMock,
  }
})
