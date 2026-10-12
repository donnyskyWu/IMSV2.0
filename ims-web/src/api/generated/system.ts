/**

 * system API - Auto-generated from OpenAPI

 * Generated at: 2026-10-12T07:15:45.837315

 * DO NOT EDIT MANUALLY

 */



import { request } from '../request';



// API Functions

/**
 * 确认保留待确认部门
 */
export async function updateDeptConfirmOrphan(params: { id: string }): Promise<CommonResult> {
  const url = '/admin-api/ims/system/dept/confirm-orphan';
  return request(url, { method: 'PUT', params });
}

/**
 * 新建部门
 */
export async function deptCreate(data: DeptCreateRequest): Promise<CommonResult_DeptResponse_> {
  const url = '/admin-api/ims/system/dept/create';
  return request(url, { method: 'POST', data });
}

/**
 * 删除部门
 */
export async function deleteDeptDelete(params: { id: string }): Promise<CommonResult> {
  const url = '/admin-api/ims/system/dept/delete';
  return request(url, { method: 'DELETE', params });
}

/**
 * 移动部门
 */
export async function updateDeptMove(data: DeptMoveRequest): Promise<CommonResult_DeptResponse_> {
  const url = '/admin-api/ims/system/dept/move';
  return request(url, { method: 'PUT', data });
}

/**
 * 获取部门树
 */
export async function getDeptTree(params: { status?: string | any; keyword?: string | any }): Promise<CommonResult_list_DeptTreeNode__> {
  const url = '/admin-api/ims/system/dept/tree';
  return request(url, { method: 'GET', params });
}

/**
 * 更新部门
 */
export async function updateDeptUpdate(params: { id: string }, data: DeptUpdateRequest): Promise<CommonResult_DeptResponse_> {
  const url = '/admin-api/ims/system/dept/update';
  return request(url, { method: 'PUT', params, data });
}

/**
 * 停用/启用部门
 */
export async function updateDeptUpdateStatus(params: { id: string; status: string }): Promise<CommonResult> {
  const url = '/admin-api/ims/system/dept/update-status';
  return request(url, { method: 'PUT', params });
}

/**
 * 获取字典值列表
 */
export async function getDictDataSimpleList(params: { dictType: string }): Promise<CommonResult_list_DictDataItem__> {
  const url = '/admin-api/ims/system/dict-data/simple-list';
  return request(url, { method: 'GET', params });
}

/**
 * 获取字典类型列表
 */
export async function getDictTypeList(): Promise<CommonResult_list_DictTypeItem__> {
  const url = '/admin-api/ims/system/dict-type/list';
  return request(url, { method: 'GET' });
}

/**
 * 获取最新同步批次
 */
export async function getOrgSyncLatestBatch(): Promise<CommonResult_OrgSyncBatchItem_> {
  const url = '/admin-api/ims/system/org-sync/latest-batch';
  return request(url, { method: 'GET' });
}

/**
 * 触发组织架构同步
 */
export async function orgSyncReconcile(): Promise<CommonResult_OrgSyncBatchItem_> {
  const url = '/admin-api/ims/system/org-sync/reconcile';
  return request(url, { method: 'POST' });
}

/**
 * 角色选择器列表
 */
export async function getRoleSimpleList(): Promise<CommonResult_list_RoleSimpleItem__> {
  const url = '/admin-api/ims/system/role/simple-list';
  return request(url, { method: 'GET' });
}

/**
 * 创建用户
 */
export async function userCreate(data: UserCreateRequest): Promise<CommonResult_UserListItem_> {
  const url = '/admin-api/ims/system/user/create';
  return request(url, { method: 'POST', data });
}

/**
 * 删除用户
 */
export async function deleteUserDelete(params: { id: string }): Promise<CommonResult> {
  const url = '/admin-api/ims/system/user/delete';
  return request(url, { method: 'DELETE', params });
}

/**
 * 用户分页列表
 */
export async function getUserPage(params: { deptId?: string | any; includeChildren?: boolean; keyword?: string | any; status?: string | any; pageNo?: number; pageSize?: number }): Promise<CommonResult_PageResult_UserListItem__> {
  const url = '/admin-api/ims/system/user/page';
  return request(url, { method: 'GET', params });
}

/**
 * 用户选择器列表
 */
export async function getUserSimplePage(params: { keyword?: string | any; pageNo?: number; pageSize?: number }): Promise<CommonResult_PageResult_UserSimpleItem__> {
  const url = '/admin-api/ims/system/user/simple-page';
  return request(url, { method: 'GET', params });
}

/**
 * 调整用户部门
 */
export async function updateUserUpdateDepts(params: { id: string; deptIds: string[]; mainDeptId: string }): Promise<CommonResult> {
  const url = '/admin-api/ims/system/user/update-depts';
  return request(url, { method: 'PUT', params });
}