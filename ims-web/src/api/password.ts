/**
 * 修改本人密码适配层（FP-B1-PW-01）
 * B0a 已冻结的 generated client 没有改密路径。
 * 契约：POST /admin-api/ims/auth/password/change { oldPassword, newPassword }
 * 后端第 2 个 PR 合入前，这里只按契约发请求，成功与否以响应 code 为准，本地不假成功。
 */
import { request } from './request'

export interface ChangePasswordPayload {
  oldPassword: string
  newPassword: string
}

export function changePassword(data: ChangePasswordPayload) {
  return request.post('/admin-api/ims/auth/password/change', data, {
    skipGlobalError: true,
  })
}
