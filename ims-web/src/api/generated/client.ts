/**
 * API 客户端封装
 * 提供类型安全的 API 调用方法
 */
import type { AxiosRequestConfig } from 'axios'
import { request } from '../request'
import type { components } from './api-types'

type Schemas = components['schemas']

// 认证相关
export const authApi = {
  login: (data: { username: string; password: string }, config?: AxiosRequestConfig) =>
    request.post<Schemas['CommonResult_LoginResponse_']>(
      '/admin-api/ims/auth/login',
      data,
      config,
    ),

  logout: () =>
    request.post<Schemas['CommonResult']>('/admin-api/ims/auth/logout'),

  refreshToken: (data: { refreshToken: string }) =>
    request.post<Schemas['CommonResult_LoginResponse_']>(
      '/admin-api/ims/auth/refresh-token',
      data
    ),

  me: () =>
    request.get<Schemas['CommonResult_MeResponse_']>('/admin-api/ims/auth/me'),
}

// 字典相关
export const dictApi = {
  getTypeList: () =>
    request.get<Schemas['CommonResult_list_DictTypeItem__']>(
      '/admin-api/ims/system/dict-type/list'
    ),

  getDataList: (params: { dictType: string }) =>
    request.get<Schemas['CommonResult_list_DictDataItem__']>(
      '/admin-api/ims/system/dict-data/simple-list',
      { params }
    ),
}

// 部门相关
export const deptApi = {
  getTree: () =>
    request.get<Schemas['CommonResult_list_DeptTreeNode__']>(
      '/admin-api/ims/system/dept/tree'
    ),

  create: (data: Schemas['DeptCreateRequest']) =>
    request.post<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/create',
      data
    ),

  update: (data: Schemas['DeptUpdateRequest']) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/update',
      data
    ),

  move: (data: Schemas['DeptMoveRequest']) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/move',
      data
    ),

  updateStatus: (data: { id: string; status: number }) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/update-status',
      data
    ),

  delete: (id: string) =>
    request.delete<Schemas['CommonResult']>(
      '/admin-api/ims/system/dept/delete',
      { params: { id } }
    ),

  confirmOrphan: (id: string) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/confirm-orphan',
      { id }
    ),
}

// 用户相关
export const userApi = {
  getPage: (params: {
    pageNo?: number
    pageSize?: number
    deptId?: string
    includeChildren?: boolean
    keyword?: string
    status?: number
  }) =>
    request.get<Schemas['CommonResult_PageResult_UserListItem__']>(
      '/admin-api/ims/system/user/page',
      { params }
    ),

  getSimplePage: (params: {
    pageNo?: number
    pageSize?: number
    keyword?: string
  }) =>
    request.get<Schemas['CommonResult_PageResult_UserSimpleItem__']>(
      '/admin-api/ims/system/user/simple-page',
      { params }
    ),

  create: (data: Schemas['UserCreateRequest']) =>
    request.post<Schemas['CommonResult_UserListItem_']>(
      '/admin-api/ims/system/user/create',
      data
    ),

  delete: (id: string) =>
    request.delete<Schemas['CommonResult']>(
      '/admin-api/ims/system/user/delete',
      { params: { id } }
    ),

  updateDepts: (data: Schemas['UserUpdateDeptsRequest']) =>
    request.put<Schemas['CommonResult_UserListItem_']>(
      '/admin-api/ims/system/user/update-depts',
      data
    ),
}

// 角色相关
export const roleApi = {
  getSimpleList: () =>
    request.get<Schemas['CommonResult_list_RoleSimpleItem__']>(
      '/admin-api/ims/system/role/simple-list'
    ),
}

// 组织同步相关
export const orgSyncApi = {
  getLatestBatch: () =>
    request.get<Schemas['CommonResult_OrgSyncBatchItem_']>(
      '/admin-api/ims/system/org-sync/latest-batch'
    ),

  reconcile: () =>
    request.post<Schemas['CommonResult_OrgSyncBatchItem_']>(
      '/admin-api/ims/system/org-sync/reconcile'
    ),
}

// 演示错误接口 (用于测试错误处理)
export const demoApi = {
  triggerError: (params: { code: number }) =>
    request.get<Schemas['CommonResult']>(
      '/admin-api/ims/demo/error',
      { params }
    ),
}
