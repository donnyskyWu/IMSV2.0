/**
 * B2 系统管理接口。手写客户端，不改 OpenAPI 生成文件。
 */
import request, { type CommonResult } from '@/api/request'

export interface DeptTreeNode {
  id: string
  name: string
  parentId?: string | null
  source?: string
  status?: string
  memberCount?: number
  children?: DeptTreeNode[]
}

export interface UserRow {
  id: string
  username: string
  nickname: string
  mobile?: string | null
  status?: string
  deptName?: string
  roleNames?: string[]
  dingtalkBound?: string
  lastLoginTime?: string | null
  locked?: boolean
}

export interface PageData<T> {
  list: T[]
  total: number
}

async function unwrap<T>(result: CommonResult<T>): Promise<T> {
  return (result.data ?? ([] as unknown as T))
}

export const systemAdminApi = {
  deptTree() {
    return request.get<CommonResult<DeptTreeNode[]>>('/admin-api/ims/system/dept/tree').then(unwrap)
  },
  deptCreate(data: { name: string; parentId: string }) {
    return request.post<CommonResult>('/admin-api/ims/system/dept/create', data)
  },
  deptMove(data: { id: string; newParentId: string }) {
    return request.put<CommonResult>('/admin-api/ims/system/dept/move', data)
  },
  deptUpdateStatus(id: string, status: string) {
    return request.put<CommonResult>('/admin-api/ims/system/dept/update-status', { id, status })
  },
  deptDelete(id: string) {
    return request.delete<CommonResult>('/admin-api/ims/system/dept/delete', { params: { id } })
  },
  orgSync() {
    return request.post<CommonResult>('/admin-api/ims/system/org-sync/reconcile')
  },
  userPage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<UserRow>>>('/admin-api/ims/system/user/page', { params }).then(unwrap)
  },
  userCreate(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/user/create', data)
  },
  userUpdate(data: Record<string, unknown>) {
    return request.put<CommonResult>('/admin-api/ims/system/user/update', data)
  },
  userUpdateStatus(data: { id: string; status: string }) {
    return request.put<CommonResult>('/admin-api/ims/system/user/update-status', data)
  },
  userResign(id: string) {
    return request.put<CommonResult>('/admin-api/ims/system/user/resign', { id })
  },
  userResetPassword(id: string) {
    return request.put<CommonResult<{ tempPassword: string }>>('/admin-api/ims/system/user/reset-password', { id })
  },
  userUnlock(id: string) {
    return request.put<CommonResult>('/admin-api/ims/system/user/unlock', { id })
  },
  userKick(id: string) {
    return request.put<CommonResult>('/admin-api/ims/system/user/kick', { id })
  },
  userDelete(id: string) {
    return request.delete<CommonResult>('/admin-api/ims/system/user/delete', { params: { id } })
  },
  userExport(data: Record<string, unknown>) {
    return request.post<CommonResult<{ taskId: string; status: string; rowCount: number }>>(
      '/admin-api/ims/system/user/export',
      data,
    )
  },
  rolePage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<Record<string, unknown>>>>('/admin-api/ims/system/role/page', { params }).then(unwrap)
  },
  roleCreate(data: { code: string; name: string }) {
    return request.post<CommonResult>('/admin-api/ims/system/role', {
      roleKey: data.code,
      name: data.name,
    })
  },
  roleUpdateMenus(id: string, data: Record<string, unknown>) {
    return request.put<CommonResult>(`/admin-api/ims/system/role/${id}/menus`, data)
  },
  roleUpdatePerm(id: string, data: Record<string, unknown>) {
    return request.put<CommonResult>(`/admin-api/ims/system/role/${id}/perm-detail`, data)
  },
  roleDataScope(id: string, data: Record<string, unknown>) {
    return request.put<CommonResult>(`/admin-api/ims/system/role/${id}/data-scope`, data, {
      skipGlobalError: true,
    })
  },
  rolePosition(id: string, data: Record<string, unknown>) {
    return request.put<CommonResult>(`/admin-api/ims/system/role/${id}/dingtalk-position`, data)
  },
  rolePreview(id: string, data: Record<string, unknown>) {
    return request.post<CommonResult>(`/admin-api/ims/system/role/${id}/preview`, data)
  },
  roleFromPosition(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/role/from-position', data)
  },
  roleMembers(id: string) {
    return request.get<CommonResult<{ list: Record<string, unknown>[] }>>(`/admin-api/ims/system/role/${id}/members`).then(unwrap)
  },
  roleRemoveMember(id: string, userId: string) {
    return request.delete<CommonResult>(`/admin-api/ims/system/role/${id}/members`, { params: { userId } })
  },
  roleDelete(id: string) {
    return request.delete<CommonResult>('/admin-api/ims/system/role/delete', {
      params: { id },
      skipGlobalError: true,
    })
  },
  roleUpdateStatus(data: { id: string; status: string }) {
    return request.put<CommonResult>('/admin-api/ims/system/role/update-status', data)
  },
  roleExport() {
    return request.post<CommonResult<{ taskId: string }>>('/admin-api/ims/system/role/export')
  },
  menuTree(params?: Record<string, unknown>) {
    return request.get<CommonResult<Record<string, unknown>[]>>('/admin-api/ims/system/menu/tree', { params }).then(unwrap)
  },
  menuCreate(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/menu/create', data)
  },
  menuUpdate(data: Record<string, unknown>) {
    return request.put<CommonResult>('/admin-api/ims/system/menu/update', data)
  },
  menuDelete(id: string) {
    return request.delete<CommonResult>('/admin-api/ims/system/menu/delete', { params: { id } })
  },
  dictTypes() {
    return request.get<CommonResult<Record<string, unknown>[]>>('/admin-api/ims/system/dict-type/list').then(unwrap)
  },
  dictTypeCreate(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/dict-type/create', data)
  },
  dictData(dictType: string) {
    return request.get<CommonResult<Record<string, unknown>[]>>('/admin-api/ims/system/dict-data/list', { params: { dictType } }).then(unwrap)
  },
  dictDataCreate(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/dict-data/create', data)
  },
  dictDataUpdate(data: Record<string, unknown>) {
    return request.put<CommonResult>('/admin-api/ims/system/dict-data/update', data)
  },
  paramList(group?: string) {
    return request.get<CommonResult<Record<string, unknown>[]>>('/admin-api/ims/system/param/list', { params: { group } }).then(unwrap)
  },
  paramUpdate(data: { paramKey: string; value: string }) {
    return request.put<CommonResult>('/admin-api/ims/system/param/update', data)
  },
  operateLogPage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<Record<string, unknown>>>>('/admin-api/ims/system/operate-log/page', { params }).then(unwrap)
  },
  operateLogDetail(id: string) {
    return request.get<CommonResult<Record<string, unknown>>>('/admin-api/ims/system/operate-log/get', { params: { id } }).then(unwrap)
  },
  loginLogPage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<Record<string, unknown>>>>('/admin-api/ims/system/login-log/page', { params }).then(unwrap)
  },
  logExport(kind: 'operate' | 'login') {
    const path = kind === 'operate' ? '/admin-api/ims/system/operate-log/export' : '/admin-api/ims/system/login-log/export'
    return request.post<CommonResult<{ taskId: string }>>(path)
  },
  notifyPage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<Record<string, unknown>>>>('/admin-api/ims/system/notify-record/page', { params }).then(unwrap)
  },
  notifyResend(id: string) {
    return request.post<CommonResult>('/admin-api/ims/system/notify-record/resend', { id })
  },
  tenantPage(params: Record<string, unknown>) {
    return request.get<CommonResult<PageData<Record<string, unknown>>>>('/admin-api/ims/system/tenant/page', { params }).then(unwrap)
  },
  tenantCreate(data: Record<string, unknown>) {
    return request.post<CommonResult<{ tempPassword?: string }>>('/admin-api/ims/system/tenant/create', data)
  },
  tenantUpdate(id: string, data: Record<string, unknown>) {
    return request.put<CommonResult>(`/admin-api/ims/system/tenant/${id}`, data)
  },
  packageList() {
    return request.get<CommonResult<Record<string, unknown>[]>>('/admin-api/ims/system/tenant-package/list').then(unwrap)
  },
  packageCreate(data: Record<string, unknown>) {
    return request.post<CommonResult>('/admin-api/ims/system/tenant-package/create', data)
  },
  mySessions() {
    return request.get<CommonResult<{ list: Record<string, unknown>[] }>>('/admin-api/ims/auth/session/my').then(unwrap)
  },
  deleteSession(sid: string) {
    return request.delete<CommonResult>('/admin-api/ims/auth/session/my', { params: { sid } })
  },
  setPassword(newPassword: string) {
    return request.post<CommonResult>('/admin-api/ims/auth/password/set', { newPassword })
  },
  me() {
    return request.get<CommonResult<Record<string, unknown>>>('/admin-api/ims/auth/me').then(unwrap)
  },
}
