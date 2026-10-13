/**
 * IMS 前端类型定义
 * 依据: B0a D2 - 前端所有 id 一律按字符串处理
 */

// 基础类型: ID 一律为字符串 (D2)
export type ID = string

// 分页请求参数
export interface PageQuery {
  pageNo?: number
  pageSize?: number
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}

// 分页响应
export interface PageResult<T> {
  list: T[]
  total: number
  pageNo: number
  pageSize: number
}

// 通用响应结构
export interface CommonResult<T = unknown> {
  code: number
  msg: string
  data: T
}

// 字段错误 (1001)
export interface FieldError {
  field: string
  message: string
}

// 菜单项
export interface MenuItem {
  id: ID
  name: string
  path?: string
  icon?: string
  permCode?: string
  /** DIR / MENU / BUTTON。真实 /me 用它区分页面和按钮。 */
  type?: string
  children?: MenuItem[]
}

// 用户信息
export interface UserInfo {
  id: ID
  username: string
  nickname: string
  avatar?: string
  deptId: ID
  deptName: string
  deptNames?: string[]
  permCodes: string[]
  dataScopeText?: string
  pwdResetRequired?: boolean
  mobileMasked?: string | null
  roleNames?: string[]
  hasPassword?: boolean
  positionLabel?: string | null
}

// 字典项
export interface DictItem {
  value: string
  label: string
  colorType?: ColorType
  status?: 'ACTIVE' | 'DISABLED'
}

// 状态色类型 (FP-T-03)
export type ColorType =
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'neutral'
  | 'info'
  | 'purple'
  | 'yellow'

// 部门节点
export interface DeptNode {
  id: ID
  name: string
  parentId: ID | null
  source: 'DINGTALK' | 'LOCAL'
  localOrphan?: boolean
  status: 'ACTIVE' | 'DISABLED'
  memberCount: number
  directMemberCount: number
  children?: DeptNode[]
}

// 抽屉尺寸
export type DrawerSize = 'S' | 'M' | 'L'

// Modal 宽度
export type ModalWidth = 360 | 520 | 800

// 空状态类型
export type EmptyType = 'empty' | 'noPermission' | 'error'

// 表格列定义
export interface TableColumn {
  key: string
  label: string
  width?: number | string
  type?: 'text' | 'mono' | 'number' | 'money' | 'percent' | 'status' | 'time' | 'masked' | 'actions'
  dictType?: string
  sortable?: boolean
  fixed?: 'left' | 'right' | boolean
}

// 查询栏字段定义
export interface QueryField {
  key: string
  label: string
  type: 'input' | 'select' | 'dict' | 'date' | 'daterange' | 'user' | 'dept'
  placeholder?: string
  options?: Array<{ value: string | number; label: string }>
  props?: Record<string, unknown>
}

// 树节点
export interface TreeNode {
  id: string | number
  label: string
  children?: TreeNode[]
  count?: number
  [key: string]: unknown
}

// 文件项
export interface FileItem {
  name: string
  url: string
  type?: string
  size?: number
}

// 流程节点
export interface FlowNode {
  id: string
  label: string
  type: 'start' | 'end' | 'task' | 'gateway' | 'condition'
  status?: 'pending' | 'running' | 'completed' | 'failed'
  x?: number
  y?: number
}

// 流程边
export interface FlowEdge {
  from: string
  to: string
  label?: string
}

// 统计卡项
export interface StatItem {
  title: string
  value: number | string | null
  unit?: string
  desc?: string
  ratio?: number
  format?: 'money' | 'percent' | 'number'
  onClick?: () => void
}

// 时间线项
export interface TimelineItem {
  time: string
  title: string
  operator?: string
  detail?: string
  colorType?: ColorType
}

// 详情字段项
export interface DescItem {
  label: string
  value: unknown
  type?: 'money' | 'percent' | 'time' | 'status' | 'masked' | 'file'
  span?: number
}
