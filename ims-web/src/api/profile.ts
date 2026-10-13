/**
 * 个人中心接口（FP-B2-PC-03 / PC-04）
 * 设置密码和会话列表不在 B0a generated client 里。
 */
import { request, type CommonResult } from './request'

export interface SessionItem {
  sid: string
  deviceName: string
  ip: string
  loginTime: string
  lastActiveTime: string
  current: boolean
}

export function setPassword(newPassword: string) {
  return request.post('/admin-api/ims/auth/password/set', { newPassword }, {
    skipGlobalError: true,
  })
}

export function listMySessions() {
  return request.get<CommonResult<{ list: SessionItem[] }>>('/admin-api/ims/auth/session/my', {
    skipGlobalError: true,
  })
}

export function deleteMySession(sid: string) {
  return request.delete('/admin-api/ims/auth/session/my', {
    params: { sid },
    skipGlobalError: true,
  })
}
