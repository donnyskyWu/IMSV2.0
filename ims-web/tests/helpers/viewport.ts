import { test, type Page } from '@playwright/test'

/** 表 A：手机视口豁免桌面数值/布局，改以 VC-M 为准。 */
export function skipOnMobile(page: Page, reason = '手机视口豁免桌面布局') {
  test.skip((page.viewportSize()?.width ?? 0) < 768, reason)
}

export function isNarrow(page: Page) {
  return (page.viewportSize()?.width ?? 1440) < 768
}
