/**
 * 选择器组件导出
 */
export { default as RemoteSelect } from './RemoteSelect.vue'
export { default as UserSelect } from './UserSelect.vue'
export { default as DeptTreeSelect } from './DeptTreeSelect.vue'
export { default as RoleSelect } from './RoleSelect.vue'
export { default as DictSelect } from './DictSelect.vue'
export { default as DateRangePicker } from './DateRangePicker.vue'

// 以下为业务选择器，使用模拟数据
// 在第 2 步接入真实 API 后替换

// RealNameSelect - 实名用户选择 (模拟)
export { default as RealNameSelect } from './UserSelect.vue'

// AccountSelect - 账号选择 (模拟)
export { default as AccountSelect } from './UserSelect.vue'

// IpGroupSelect - IP 组选择 (可复用 RemoteSelect)
// AuthorSelect - 作者选择 (可复用 UserSelect)
// CompanySelect - 公司选择 (可复用 RemoteSelect)
// MatchSelect - 匹配选择 (可复用 DictSelect)
