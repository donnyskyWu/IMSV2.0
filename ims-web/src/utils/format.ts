/**
 * 格式化工具函数
 * 依据: FP-R-08, 02-前端基础层清单 §1.6
 */

/**
 * 格式化金额
 * @param value 金额值 (字符串或数字)
 * @returns 格式化后的金额字符串, 如 "¥1,234.50"
 */
export function fmtMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '—'
  }

  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) {
    return '—'
  }

  const formatted = new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(num))

  return num < 0 ? `-${formatted}` : formatted
}

/**
 * 格式化百分比
 * @param value 百分比值 (如 5 表示 5%)
 * @returns 格式化后的百分比字符串
 */
export function fmtPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return `${value}%`
}

/**
 * 格式化日期时间
 * @param value ISO 时间字符串
 * @returns 格式化后的时间 "YYYY-MM-DD HH:mm"
 */
export function fmtDateTime(value: string | null | undefined): string {
  return fmtTime(value)
}

/**
 * 格式化时间
 * @param value ISO 时间字符串
 * @returns 格式化后的时间 "YYYY-MM-DD HH:mm"
 */
export function fmtTime(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }

  try {
    const date = new Date(value)
    if (isNaN(date.getTime())) {
      return '—'
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch {
    return '—'
  }
}

/**
 * 格式化日期
 * @param value ISO 时间字符串
 * @returns 格式化后的日期 "YYYY-MM-DD"
 */
export function fmtDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }

  try {
    const date = new Date(value)
    if (isNaN(date.getTime())) {
      return '—'
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  } catch {
    return '—'
  }
}

/**
 * 格式化周期范围
 * @param start 开始日期
 * @param end 结束日期
 * @returns "2026-10-05 ~ 2026-10-11"
 */
export function fmtPeriod(
  start: string | null | undefined,
  end: string | null | undefined
): string {
  const startStr = fmtDate(start)
  const endStr = fmtDate(end)

  if (startStr === '—' && endStr === '—') {
    return '—'
  }

  return `${startStr} ~ ${endStr}`
}

/**
 * 判断是否为空值
 */
export function isEmpty(value: unknown): boolean {
  return value === null || value === undefined || value === ''
}

/**
 * 显示空值占位符
 */
export function emptyPlaceholder(value: unknown): string {
  return isEmpty(value) ? '—' : String(value)
}
