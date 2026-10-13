import { describe, expect, it } from 'vitest'
import { greetingForHour } from './greeting'

describe('greetingForHour', () => {
  it('凌晨档在 5 点前，其余沿用 5/11/13/18 边界', () => {
    expect(greetingForHour(0)).toBe('凌晨好')
    expect(greetingForHour(4)).toBe('凌晨好')
    expect(greetingForHour(5)).toBe('早上好')
    expect(greetingForHour(10)).toBe('早上好')
    expect(greetingForHour(11)).toBe('中午好')
    expect(greetingForHour(13)).toBe('下午好')
    expect(greetingForHour(18)).toBe('晚上好')
    expect(greetingForHour(23)).toBe('晚上好')
  })
})
