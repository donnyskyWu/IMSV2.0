/**
 * Training module API client (B21)
 * Auto-generated based on backend API spec
 */
import { request } from '../request'

// Types
export interface TrainMaterialCate {
  id: string
  parentId?: string | null
  positionCode?: string | null
  cateName: string
  sort: number
  children?: TrainMaterialCate[]
}

export interface TrainMaterial {
  id: string
  materialNo: string
  title: string
  cateId: string
  cateName?: string
  materialType: 'DOC' | 'VIDEO' | 'LINK'
  fileKey?: string | null
  linkUrl?: string | null
  positionCodes?: string[]
  version: number
  status: 'DRAFT' | 'PUBLISHED' | 'OFFLINE'
  convertStatus?: 'PENDING' | 'DONE' | 'FAILED' | null
  pageCount?: number | null
  durationSeconds?: number | null
  publishedAt?: string | null
  uploaderUserName?: string
  createTime: string
  updateTime: string
}

export interface TrainMaterialDetail extends TrainMaterial {
  versions: TrainMaterialVersion[]
}

export interface TrainMaterialVersion {
  id: string
  version: number
  title: string
  fileKey?: string | null
  pdfKey?: string | null
  linkUrl?: string | null
  pageCount?: number | null
  durationSeconds?: number | null
  editorUserName?: string
  createdAt: string
}

export interface TrainTask {
  id: string
  taskNo: string
  taskName: string
  materialIds: string[]
  assignScope: 'BY_USER' | 'BY_POSITION'
  deadline: string
  confirmType: 'DURATION' | 'QUIZ'
  requiredMinutes?: number
  passScore?: number
  status: 'IN_PROGRESS' | 'FINISHED'
  source: 'MANUAL' | 'ONBOARDING'
  creatorDeptName?: string
  assignedCount: number
  finishedCount: number
  createTime: string
}

export interface TrainTaskDetail extends TrainTask {
  materials: TrainMaterial[]
  quiz?: QuizQuestion[]
  records?: TrainTaskRecord[]
}

export interface TrainTaskRecord {
  id: string
  taskId: string
  userId: string
  userName: string
  userDeptName?: string
  progress: number
  effectiveSeconds: number
  confirmStatus: 'NOT_CONFIRMED' | 'CONFIRMED'
  confirmScore?: number | null
  startedAt?: string | null
  finishedAt?: string | null
  isOverdue: boolean
}

export interface QuizQuestion {
  type: 'SINGLE' | 'TRUE_FALSE'
  question: string
  options?: string[]
  answerIndex?: number
  answerBoolean?: boolean
}

export interface TrainStudyTask {
  taskId: string
  taskName: string
  deadline: string
  confirmType: 'DURATION' | 'QUIZ'
  requiredMinutes?: number
  progress: number
  effectiveMinutes: number
  confirmStatus: 'NOT_CONFIRMED' | 'CONFIRMED'
  materials: TrainStudyMaterial[]
}

export interface TrainStudyMaterial {
  materialId: string
  title: string
  materialType: 'DOC' | 'VIDEO' | 'LINK'
  progress: number
  durationSeconds?: number
  pageCount?: number
  linkUrl?: string
  fileKey?: string
  pdfKey?: string
}

export interface TrainStatFinishRate {
  totalAssigned: number
  totalFinished: number
  totalOverdue: number
  finishRate: number
  overdueRate: number
}

export interface TrainStatDept {
  deptId: string
  deptName: string
  assignedCount: number
  finishedCount: number
  overdueCount: number
  finishRate: number
  totalMinutes: number
  avgMinutes: number
}

export interface TrainStatRank {
  userId: string
  userName: string
  deptName: string
  totalMinutes: number
  taskCount: number
}

export interface TrainStatOverdue {
  recordId: string
  userId: string
  userName: string
  deptName: string
  taskName: string
  deadline: string
  overduedays: number
}

export interface TrainMaterialHeat {
  materialId: string
  title: string
  materialType: string
  viewCount: number
  finishCount: number
}

// API Functions

// Category Management
export async function getCateTree(params?: { positionCode?: string }) {
  return request<TrainMaterialCate[]>({
    url: '/admin-api/ims/train/material/cates',
    method: 'GET',
    params,
  })
}

export async function createCate(data: { parentId: string; cateName: string; positionCode?: string; sort?: number }) {
  return request<TrainMaterialCate>({
    url: '/admin-api/ims/train/material/cate',
    method: 'POST',
    data,
  })
}

export async function updateCate(id: string, data: { cateName?: string; sort?: number }) {
  return request<TrainMaterialCate>({
    url: `/admin-api/ims/train/material/cate/${id}`,
    method: 'PUT',
    data,
  })
}

export async function deleteCate(id: string) {
  return request({
    url: `/admin-api/ims/train/material/cate/${id}`,
    method: 'DELETE',
  })
}

// Material Management
export async function getMaterialList(params: {
  cateId?: string
  keyword?: string
  status?: string
  materialType?: string
  pageNo?: number
  pageSize?: number
}) {
  return request<{ list: TrainMaterial[]; total: number; pageNo: number; pageSize: number }>({
    url: '/admin-api/ims/train/material/list',
    method: 'GET',
    params,
  })
}

export async function getMaterialDetail(id: string) {
  return request<TrainMaterialDetail>({
    url: `/admin-api/ims/train/material/${id}`,
    method: 'GET',
  })
}

export async function createMaterial(data: {
  title: string
  cateId: string
  materialType: string
  fileKey?: string
  linkUrl?: string
  positionCodes?: string[]
  status?: string
}) {
  return request<TrainMaterial>({
    url: '/admin-api/ims/train/material',
    method: 'POST',
    data,
  })
}

export async function updateMaterial(id: string, data: {
  title?: string
  cateId?: string
  fileKey?: string
  linkUrl?: string
  positionCodes?: string[]
  status?: string
}) {
  return request<TrainMaterial>({
    url: `/admin-api/ims/train/material/${id}`,
    method: 'PUT',
    data,
  })
}

export async function offlineMaterial(id: string) {
  return request({
    url: `/admin-api/ims/train/material/${id}`,
    method: 'DELETE',
  })
}

export async function getWeeklyUpdateMetrics() {
  return request<{ weeklyUpdateRate: number; totalMaterials: number; updatedThisWeek: number }>({
    url: '/admin-api/ims/train/material/weekly-update-metrics',
    method: 'GET',
  })
}

// Task Management
export async function getTaskList(params: {
  keyword?: string
  status?: string
  confirmType?: string
  pageNo?: number
  pageSize?: number
}) {
  return request<{ list: TrainTask[]; total: number; pageNo: number; pageSize: number }>({
    url: '/admin-api/ims/train/task/list',
    method: 'GET',
    params,
  })
}

export async function getTaskDetail(id: string) {
  return request<TrainTaskDetail>({
    url: `/admin-api/ims/train/task/${id}`,
    method: 'GET',
  })
}

export async function createTask(data: {
  taskName: string
  materialIds: string[]
  assignScope: string
  assignedUserIds?: string[]
  assignedPositionCodes?: string[]
  deadline: string
  confirmType: string
  requiredMinutes?: number
  quiz?: QuizQuestion[]
  passScore?: number
  clientToken: string
}) {
  return request<TrainTask>({
    url: '/admin-api/ims/train/task',
    method: 'POST',
    data,
  })
}

export async function updateTask(id: string, data: {
  taskName?: string
  materialIds?: string[]
  assignedUserIds?: string[]
  deadline?: string
  requiredMinutes?: number
}) {
  return request<TrainTask>({
    url: `/admin-api/ims/train/task/${id}`,
    method: 'PUT',
    data,
  })
}

export async function deleteTask(id: string) {
  return request({
    url: `/admin-api/ims/train/task/${id}`,
    method: 'DELETE',
  })
}

export async function previewPositionUsers(positionCodes: string[]) {
  return request<{ count: number; users: { id: string; nickname: string; deptName: string }[] }>({
    url: '/admin-api/ims/train/task/position-preview',
    method: 'GET',
    params: { positionCodes: positionCodes.join(',') },
  })
}

export async function getTaskRecords(params: {
  taskId?: string
  userId?: string
  confirmStatus?: string
  isOverdue?: boolean
  pageNo?: number
  pageSize?: number
}) {
  return request<{ list: TrainTaskRecord[]; total: number; pageNo: number; pageSize: number }>({
    url: '/admin-api/ims/train/task/records',
    method: 'GET',
    params,
  })
}

// Study Execution
export async function getMyTasks(params?: { status?: string; pageNo?: number; pageSize?: number }) {
  return request<{ list: TrainStudyTask[]; total: number; pageNo: number; pageSize: number }>({
    url: '/admin-api/ims/train/study/my-tasks',
    method: 'GET',
    params,
  })
}

export async function getStudyTaskDetail(taskId: string) {
  return request<TrainStudyTask>({
    url: `/admin-api/ims/train/study/task/${taskId}`,
    method: 'GET',
  })
}

export async function reportProgress(taskId: string, data: {
  materialId: string
  position: number
  intervalSeconds: number
}) {
  return request<{ effectiveSeconds: number; progress: number }>({
    url: `/admin-api/ims/train/task/${taskId}/progress`,
    method: 'PUT',
    data,
  })
}

export async function saveQuizDraft(taskId: string, data: { answers: Record<number, number | boolean> }) {
  return request({
    url: `/admin-api/ims/train/task/${taskId}/quiz-draft`,
    method: 'PUT',
    data,
  })
}

export async function confirmTask(taskId: string, data?: { answers?: Record<number, number | boolean> }) {
  return request<{ confirmed: boolean; score?: number; passed?: boolean }>({
    url: `/admin-api/ims/train/task/${taskId}/confirm`,
    method: 'POST',
    data,
  })
}

// Statistics
export async function getFinishRate(params?: { deptId?: string; startDate?: string; endDate?: string }) {
  return request<TrainStatFinishRate>({
    url: '/admin-api/ims/train/stat/finish-rate',
    method: 'GET',
    params,
  })
}

export async function getDeptStat(params?: { deptId?: string; statDate?: string }) {
  return request<{ list: TrainStatDept[] }>({
    url: '/admin-api/ims/train/stat/dept',
    method: 'GET',
    params,
  })
}

export async function getRank(params?: { deptId?: string; limit?: number }) {
  return request<{ list: TrainStatRank[] }>({
    url: '/admin-api/ims/train/stat/rank',
    method: 'GET',
    params,
  })
}

export async function getOverdueList(params?: { deptId?: string; pageNo?: number; pageSize?: number }) {
  return request<{ list: TrainStatOverdue[]; total: number; pageNo: number; pageSize: number }>({
    url: '/admin-api/ims/train/stat/overdue',
    method: 'GET',
    params,
  })
}

export async function exportOverdue(params?: { deptId?: string }) {
  return request<{ taskId: string }>({
    url: '/admin-api/ims/train/stat/overdue/export',
    method: 'POST',
    data: params,
  })
}

export async function getMaterialHeat(params?: { limit?: number }) {
  return request<{ list: TrainMaterialHeat[] }>({
    url: '/admin-api/ims/train/stat/material-heat',
    method: 'GET',
    params,
  })
}

// AI Quiz Generation
export async function generateQuizByAI(data: { materialIds: string[]; questionCount?: number; difficulty?: string }) {
  return request<{ questions: QuizQuestion[] }>({
    url: '/admin-api/ims/train/quiz/ai-generate',
    method: 'POST',
    data,
  })
}
