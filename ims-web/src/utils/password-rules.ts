/**
 * 强制改密校验（FP-B1-PW-01，工作包 Q7）
 * 8～32 位且同时含字母和数字；允许特殊字符；不允许空格；不校验历史密码。
 */

export interface PasswordFormValues {
  oldPassword: string
  newPassword: string
  confirmPassword: string
}

export interface PasswordFieldErrors {
  oldPassword?: string
  newPassword?: string
  confirmPassword?: string
}

export const PASSWORD_COPY = {
  oldRequired: '请输入当前密码',
  newRequired: '请输入新密码',
  confirmRequired: '请输入确认新密码',
  rule: '密码需 8～32 位，且同时包含字母和数字',
  space: '密码不能包含空格',
  same: '新密码不能与当前密码相同',
  mismatch: '两次输入的新密码不一致',
  wrongOld: '当前密码不正确',
  updated: '密码已修改',
} as const

const PASSWORD_PATTERN = /^(?=.*[A-Za-z])(?=.*\d)\S{8,32}$/

export function validatePasswordChange(values: PasswordFormValues): PasswordFieldErrors {
  const errors: PasswordFieldErrors = {}
  if (!values.oldPassword) errors.oldPassword = PASSWORD_COPY.oldRequired

  if (!values.newPassword) {
    errors.newPassword = PASSWORD_COPY.newRequired
  } else if (/\s/.test(values.newPassword)) {
    errors.newPassword = PASSWORD_COPY.space
  } else if (!PASSWORD_PATTERN.test(values.newPassword)) {
    errors.newPassword = PASSWORD_COPY.rule
  } else if (values.oldPassword && values.newPassword === values.oldPassword) {
    errors.newPassword = PASSWORD_COPY.same
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = PASSWORD_COPY.confirmRequired
  } else if (values.newPassword && values.confirmPassword !== values.newPassword) {
    errors.confirmPassword = PASSWORD_COPY.mismatch
  }
  return errors
}

export function hasPasswordErrors(errors: PasswordFieldErrors): boolean {
  return Boolean(errors.oldPassword || errors.newPassword || errors.confirmPassword)
}
