/**
 * 工作台 API 客户端（B3 新建）
 * 依据: 个人工作台-实现理解 §3
 */
import { request, type CommonResult } from './request'

// ============== Types ==============

export interface DashboardData {
  todoCount: number
  todoByType: Record<string, number>
  todoOverdue: number
  unreadMessageCount: number
  myAccountCount: number | null
  myAssetCount: number | null
  myApprovalCount: number | null
  myAttendanceCount: number | null
}

export interface TodoItem {
  id: string
  type: string | null
  title: string
  content: string | null
  sourceModule: string | null
  sourceType: string | null
  sourceId: string | null
  route: string | null
  status: string
  dueTime: string | null
  isOverdue: boolean
  overdueDays: number
  createTime: string | null
  doneTime: string | null
  doneBy: string | null
  doneByName: string | null
}

export interface TodoPageResponse {
  total: number
  pageNo: number
  pageSize: number
  list: TodoItem[]
}

export interface TodoCountResponse {
  total: number
  byType: Record<string, number>
  overdue: number
}

export interface MessageItem {
  id: string
  title: string
  body: string
  eventType: string | null
  sourceModule: string | null
  route: string | null
  refType: string | null
  refId: string | null
  readStatus: string
  readTime: string | null
  createTime: string | null
}

export interface MessagePageResponse {
  total: number
  pageNo: number
  pageSize: number
  list: MessageItem[]
}

export interface MarkReadResponse {
  updated: number
}

// ============== API ==============

const BASE_URL = '/admin-api/ims'

export const workbenchApi = {
  /** 获取工作台仪表盘数据 */
  getDashboard(): Promise<CommonResult<DashboardData>> {
    return request.get(`${BASE_URL}/auth/workbench/dashboard`)
  },
}

export const todoApi = {
  /** 我的待办分页 */
  getMyPage(params: {
    type?: string
    status?: string
    keyword?: string
    pageNo?: number
    pageSize?: number
  }): Promise<CommonResult<TodoPageResponse>> {
    const queryParams = new URLSearchParams()
    if (params.type) queryParams.set('type', params.type)
    if (params.status) queryParams.set('status', params.status)
    if (params.keyword) queryParams.set('keyword', params.keyword)
    if (params.pageNo) queryParams.set('page_no', String(params.pageNo))
    if (params.pageSize) queryParams.set('page_size', String(params.pageSize))
    const query = queryParams.toString()
    return request.get(`${BASE_URL}/todo/my/page${query ? `?${query}` : ''}`)
  },

  /** 我的待办计数 */
  getMyCount(): Promise<CommonResult<TodoCountResponse>> {
    return request.get(`${BASE_URL}/todo/my/count`)
  },

  /** 我的待办详情 */
  getMyDetail(id: string): Promise<CommonResult<TodoItem>> {
    return request.get(`${BASE_URL}/todo/my/get?id=${id}`)
  },

  /** 关闭待办 */
  close(id: string): Promise<CommonResult<null>> {
    return request.put(`${BASE_URL}/todo/my/close`, { id: Number(id) })
  },
}

export const messageApi = {
  /** 我的消息分页 */
  getMyPage(params: {
    readStatus?: string
    keyword?: string
    pageNo?: number
    pageSize?: number
  }): Promise<CommonResult<MessagePageResponse>> {
    const queryParams = new URLSearchParams()
    if (params.readStatus) queryParams.set('read_status', params.readStatus)
    if (params.keyword) queryParams.set('keyword', params.keyword)
    if (params.pageNo) queryParams.set('page_no', String(params.pageNo))
    if (params.pageSize) queryParams.set('page_size', String(params.pageSize))
    const query = queryParams.toString()
    return request.get(`${BASE_URL}/message/my/page${query ? `?${query}` : ''}`)
  },

  /** 未读消息数 */
  getUnreadCount(): Promise<CommonResult<number>> {
    return request.get(`${BASE_URL}/message/my/unread-count`)
  },

  /** 消息详情 */
  getMyDetail(id: string): Promise<CommonResult<MessageItem>> {
    return request.get(`${BASE_URL}/message/my/get?id=${id}`)
  },

  /** 标记已读 */
  markRead(ids: string[]): Promise<CommonResult<MarkReadResponse>> {
    return request.post(`${BASE_URL}/message/my/read`, { ids: ids.map(Number) })
  },

  /** 全部已读 */
  markAllRead(): Promise<CommonResult<MarkReadResponse>> {
    return request.post(`${BASE_URL}/message/my/read-all`)
  },
}
