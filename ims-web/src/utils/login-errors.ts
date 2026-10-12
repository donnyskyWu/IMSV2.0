/**
 * 登录失败文案（FP-B1-LG-03，错误码以 01 §0.4 / B0a 已登记码为准）
 * 页面只展示白名单文案，不把接口 msg 原样写进页面。
 */

export const LOGIN_COPY = {
  usernameRequired: '请输入用户名',
  passwordRequired: '请输入密码',
  wrongPassword: '用户名或密码错误',
  frozen: '账号已冻结或已离职，无法登录，请联系管理员',
  tenantDisabled: '所属组织已停用，请联系管理员',
  busy: '系统繁忙，请稍后再试',
  network: '网络异常，请检查网络后重试',
} as const

export function lockMessage(minutes: number): string {
  return `账号已锁定，请 ${minutes} 分钟后再试`
}

/** 1215：优先读 B1 约定的 data.remainMinutes，否则从 B0a 文案里的分钟数解析。 */
export function parseLockMinutes(data: unknown, msg: string): number {
  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>
    const raw = record.remainMinutes ?? record.n
    const minutes = Number(raw)
    if (Number.isFinite(minutes) && minutes > 0) return Math.ceil(minutes)
  }
  const matched = /请\s*(\d+)\s*分钟/.exec(msg)
  if (matched) return Number(matched[1])
  return 15
}
