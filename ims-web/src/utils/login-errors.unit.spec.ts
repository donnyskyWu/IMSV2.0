/**
 * 登录失败文案单测（FP-B1-LG-03）。
 */
import { describe, expect, it } from 'vitest'
import { lockMessage, parseLockMinutes } from './login-errors'

describe('lockMessage', () => {
  it('按分钟数拼锁定文案', () => {
    expect(lockMessage(15)).toBe('账号已锁定，请 15 分钟后再试')
  })
})

describe('parseLockMinutes', () => {
  it('优先读 remainMinutes，其次 n，再从文案解析，否则 15', () => {
    expect(parseLockMinutes({ remainMinutes: 8 }, '账号已锁定，请 1 分钟后再试')).toBe(8)
    expect(parseLockMinutes({ remainMinutes: 1.2 }, '')).toBe(2)
    expect(parseLockMinutes({ n: 3 }, '')).toBe(3)
    expect(parseLockMinutes({ remainMinutes: 0 }, '请 6 分钟')).toBe(6)
    expect(parseLockMinutes({ remainMinutes: 'no' }, '没有分钟')).toBe(15)
    expect(parseLockMinutes(null, '请 4 分钟后再试')).toBe(4)
    expect(parseLockMinutes('bad', '')).toBe(15)
  })
})
