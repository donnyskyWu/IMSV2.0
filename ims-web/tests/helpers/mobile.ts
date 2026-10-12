/**
 * 移动端测试辅助函数
 * 依据: 02-验证用例.md §移动端 390×844 视口验证
 */
import { type Page, type Locator, expect } from '@playwright/test'

export const BP_MOBILE = 768
export const MIN_TOUCH = 44
export const MIN_GAP = 8
export const MIN_GAP_SMALL = 18 // §2.3 U1: 小号按钮之间的视觉间距 ≥18px
export const MIN_FONT = 12
export const INPUT_FONT = 16
export const VW = 390

/**
 * 断言页面无横向溢出
 */
export async function expectNoHOverflow(page: Page, w = VW): Promise<void> {
  await expect
    .poll(async () => {
      return page.evaluate(() =>
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)
      )
    })
    .toBeLessThanOrEqual(w)
}

/**
 * 断言元素在视口内
 */
export async function expectInViewport(locator: Locator, viewportWidth = VW): Promise<void> {
  const box = await locator.boundingBox()
  expect(box).not.toBeNull()
  if (box) {
    expect(box.x).toBeGreaterThanOrEqual(-0.5)
    expect(box.x + box.width).toBeLessThanOrEqual(viewportWidth + 0.5)
  }
}

/**
 * 收集页面错误 (不含 warning)
 */
export async function collectErrors(page: Page): Promise<string[]> {
  const errors: string[] = []

  page.on('pageerror', (error) => {
    errors.push(`PageError: ${error.message}`)
  })

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`ConsoleError: ${msg.text()}`)
    }
  })

  return errors
}

/**
 * 计算元素的热区大小
 * 以元素中心为原点向外扩展 22px，检测边界内侧 1px 处是否命中目标
 */
export async function hitBox(locator: Locator): Promise<{ width: number; height: number }> {
  const box = await locator.boundingBox()
  if (!box) {
    return { width: 0, height: 0 }
  }

  const result = await locator.evaluate((el) => {
    const rect = el.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    let hitWidth = rect.width
    let hitHeight = rect.height

    const checkHit = (x: number, y: number): boolean => {
      const hit = document.elementFromPoint(x, y)
      return hit === el || el.contains(hit)
    }

    for (let expand = 1; expand <= 22; expand++) {
      if (checkHit(centerX - rect.width / 2 - expand, centerY)) {
        hitWidth = rect.width + expand * 2
      }
      if (checkHit(centerX, centerY - rect.height / 2 - expand)) {
        hitHeight = rect.height + expand * 2
      }
    }

    return { width: hitWidth, height: hitHeight }
  })

  return result
}

/**
 * 判断是否为移动视口
 */
export function isMobileViewport(page: Page): boolean {
  const viewport = page.viewportSize()
  return viewport ? viewport.width < BP_MOBILE : false
}

/**
 * 判断是否为桌面视口
 */
export function isDesktopViewport(page: Page): boolean {
  const viewport = page.viewportSize()
  return viewport ? viewport.width >= BP_MOBILE : false
}
