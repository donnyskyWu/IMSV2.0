export interface TodoTab {
  key: string
  label: string
}

/** 待办类型 Tab。文案与产品复核一致，首页和待办中心共用。 */
export const TODO_TABS: TodoTab[] = [
  { key: 'all', label: '全部待办' },
  { key: 'APPROVAL', label: '审批待办' },
  { key: 'RETURN', label: '归还待办' },
  { key: 'REVIEW', label: '审核待办' },
  { key: 'CONFIRM', label: '确认待办' },
  { key: 'WARNING', label: '预警待办' },
  { key: 'ALERT', label: '告警待办' },
]

const TYPE_META: Record<string, { text: string; type: 'primary' | 'warning' | 'info' | 'success' | 'danger' | '' }> = {
  APPROVAL: { text: '审批待办', type: 'primary' },
  RETURN: { text: '归还待办', type: 'warning' },
  REVIEW: { text: '审核待办', type: 'info' },
  CONFIRM: { text: '确认待办', type: 'success' },
  WARNING: { text: '预警待办', type: 'warning' },
  ALERT: { text: '告警待办', type: 'danger' },
  STUDY: { text: '学习待办', type: '' },
}

export function todoTypeInfo(type: string | null) {
  return TYPE_META[type || ''] || { text: '待办', type: '' as const }
}

/** 状态列只用中文。已过期是 PENDING 且逾期，不展示状态码。 */
export function todoStatusText(status: string, isOverdue: boolean): string {
  if (status === 'DONE') return '已处理'
  if (isOverdue) return '已过期'
  return '待处理'
}

export function overdueText(isOverdue: boolean, days: number): string {
  if (!isOverdue) return ''
  if (!days) return '已过期'
  return `过期 ${days} 天`
}

export function canCloseTodo(type: string | null): boolean {
  return type !== 'APPROVAL' && type !== 'REVIEW'
}

export function isTodoTabKey(key: string): boolean {
  return TODO_TABS.some((tab) => tab.key === key)
}
