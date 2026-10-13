/**
 * Organization sync API types and endpoints (FP-B1-ORG-01~11)
 */
import { request } from './request'

export interface SyncMetrics {
  userTotal: number
  yesterdayEventCount: number
  pendingEventCount: number
  deadEventCount: number
  avgDelayMinutes: number
  p95DelayMinutes: number
  successRate24h: number
  dingtalkUnavailable: boolean
  reconcileFailedTwice: boolean
}

export interface SyncEvent {
  id: string
  eventId: string
  eventType: string | null
  bizType: string | null
  subjectUserId: string | null
  subjectName: string | null
  deptId: string | null
  beforeDeptNames: string | null
  afterDeptNames: string | null
  status: string
  retryCount: number
  lastError: string | null
  eventTime: string | null
  receivedTime: string | null
  processedTime: string | null
  delaySeconds: number | null
  attempts?: EventAttempt[]
}

export interface EventAttempt {
  attempt_no: number
  trigger: string
  operator_id: string | null
  start_time: string | null
  end_time: string | null
  result: string | null
  error_msg: string | null
}

export interface DiffSummary {
  overrideCount: number
  pendingAssignCount: number
  localOrphanCount: number
  sameNameCount: number
  unboundCount: number
}

export interface ReconcileBatch {
  id: string
  triggerType: string | null
  status: string
  startedAt: string | null
  completedAt: string | null
  diffCount: number
  fixedCount: number
  failReason: string | null
}

export interface ReconcileBatchDetail extends ReconcileBatch {
  operatorId: string | null
  addedDepts: number
  updatedDepts: number
  removedDepts: number
  addedUsers: number
  updatedUsers: number
  removedUsers: number
  errorMsg: string | null
}

export interface ReconcileBatchItem {
  id: string
  objectType: string
  objectId: string | null
  objectName: string | null
  deptId: string | null
  action: string | null
  beforeValue: string | null
  afterValue: string | null
  result: string | null
  errorMsg: string | null
}

export interface UserDetail {
  id: string
  nickname: string
  empNo: string | null
  username: string
  status: string
  mainDeptName: string | null
  deptNames: string[]
  positionLabel: string | null
  dingtalkBound: boolean
  lastSyncTime: string | null
  source: string
  roles: UserRole[]
  dataScopeText: string | null
  menuCount: number
  recentEvents: RecentEvent[]
}

export interface UserRole {
  id: string
  name: string
  source: string
  status: string
  revokeAt: string | null
}

export interface RecentEvent {
  id: string
  eventType: string | null
  eventTime: string | null
  status: string
}

export interface EventListParams {
  keyword?: string
  deptId?: string
  eventTypes?: string
  statuses?: string
  startTime?: string
  endTime?: string
  sortBy?: string
  sortOrder?: string
  pageNo?: number
  pageSize?: number
}

export interface ReplayRequest {
  startTime: string
  endTime: string
  statuses: string[]
}

export const orgSyncApi = {
  getMetrics: () => request.get<SyncMetrics>('/admin-api/ims/auth/org/sync-metrics'),

  getDiffSummary: () => request.get<DiffSummary>('/admin-api/ims/auth/org/diffs/summary'),

  getEvents: (params: EventListParams) =>
    request.get('/admin-api/ims/auth/org/events', { params }),

  getEventDetail: (id: string) =>
    request.get<SyncEvent>(`/admin-api/ims/auth/org/events/${id}`),

  retryEvent: (id: string) =>
    request.post(`/admin-api/ims/auth/org/events/${id}/retry`),

  getReplayPreview: (params: { startTime: string; endTime: string; statuses: string }) =>
    request.get<{ count: number }>('/admin-api/ims/auth/org/events/replay-preview', { params }),

  replay: (data: ReplayRequest) =>
    request.post('/admin-api/ims/auth/org/events/replay', data),

  getReconcileBatches: (params: {
    startTime?: string
    endTime?: string
    triggerTypes?: string
    statuses?: string
    pageNo?: number
    pageSize?: number
  }) => request.get('/admin-api/ims/auth/org/reconcile-batches', { params }),

  getReconcileBatchDetail: (id: string) =>
    request.get<ReconcileBatchDetail>(`/admin-api/ims/auth/org/reconcile-batches/${id}`),

  getReconcileBatchItems: (
    id: string,
    params: { result?: string; pageNo?: number; pageSize?: number }
  ) => request.get(`/admin-api/ims/auth/org/reconcile-batches/${id}/items`, { params }),

  getUserDetail: (id: string) =>
    request.get<UserDetail>(`/admin-api/ims/auth/org/users/${id}`),

  exportEvents: () => request.post('/admin-api/ims/auth/org/events/export'),

  triggerReconcile: () => request.post('/admin-api/ims/system/org-sync/reconcile'),
}
