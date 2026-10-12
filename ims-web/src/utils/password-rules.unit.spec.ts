/**
 * 强制改密校验单测（FP-B1-PW-01 / Q7）。
 */
import { describe, expect, it } from 'vitest'
import { PASSWORD_COPY, hasPasswordErrors, validatePasswordChange } from './password-rules'

describe('validatePasswordChange', () => {
  it('空表单分别提示三个必填', () => {
    const errors = validatePasswordChange({ oldPassword: '', newPassword: '', confirmPassword: '' })
    expect(errors.oldPassword).toBe(PASSWORD_COPY.oldRequired)
    expect(errors.newPassword).toBe(PASSWORD_COPY.newRequired)
    expect(errors.confirmPassword).toBe(PASSWORD_COPY.confirmRequired)
    expect(hasPasswordErrors(errors)).toBe(true)
  })

  it('空格、位数、与当前相同、两次不一致都拦截', () => {
    expect(validatePasswordChange({
      oldPassword: 'Test1234',
      newPassword: 'Abcd 5678',
      confirmPassword: 'Abcd 5678',
    }).newPassword).toBe(PASSWORD_COPY.space)
    expect(validatePasswordChange({
      oldPassword: 'Test1234',
      newPassword: 'abcdefgh',
      confirmPassword: 'abcdefgh',
    }).newPassword).toBe(PASSWORD_COPY.rule)
    expect(validatePasswordChange({
      oldPassword: 'Test1234',
      newPassword: 'Test1234',
      confirmPassword: 'Test1234',
    }).newPassword).toBe(PASSWORD_COPY.same)
    expect(validatePasswordChange({
      oldPassword: 'Test1234',
      newPassword: 'Abcd5678',
      confirmPassword: 'Abcd5679',
    }).confirmPassword).toBe(PASSWORD_COPY.mismatch)
  })

  it('字母数字加特殊字符可以通过，且不校验历史密码', () => {
    const errors = validatePasswordChange({
      oldPassword: 'Test1234',
      newPassword: 'Abcd5678!',
      confirmPassword: 'Abcd5678!',
    })
    expect(errors).toEqual({})
    expect(hasPasswordErrors(errors)).toBe(false)
  })
})
