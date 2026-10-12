/**
 * 展示组件测试
 * 依据: 02-验证用例.md VC-C37~C41, VC-R-17
 */
import { test, expect } from '@playwright/test'
import { skipOnMobile } from './helpers/viewport'

test.describe('C37～C41. 展示组件', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/display')
    await page.waitForSelector('.display-demo')
  })

  test('VC-R-17: 金额百分比时间空值格式化', async ({ page }) => {
    const money = page.locator('.money-text').first()
    await expect(money).toBeVisible()
    await expect(money).toContainText(/¥|￥/)
    await expect(money).toContainText(/\d+\.\d{2}/)
    const negative = page.locator('.money-text--negative')
    await expect(negative).toBeVisible()
    const color = await negative.evaluate((el) => getComputedStyle(el).color)
    expect(color).toMatch(/rgb\(255,\s*59,\s*48\)/)
    await expect(page.locator('.percent-text')).toContainText('85.5%')
    await expect(page.locator('.description-list').getByText('—')).toBeVisible()
  })

  test('VC-C37-01: 时间线最新在上可展开', async ({ page }) => {
    const items = page.locator('.timeline-item')
    await expect(items).toHaveCount(4)
    await expect(items.first()).toContainText('审批完成')
    await expect(items.last()).toContainText('订单创建')
    await expect(items.first().locator('.timeline-body')).toBeVisible()
  })

  test('VC-C38-01: 详情字段标签列宽空值横线', async ({ page }) => {
    skipOnMobile(page, '手机下详情字段单列，标签列宽另测')
    const list = page.locator('.description-list')
    await expect(list).toBeVisible()
    const label = list.locator('.desc-label').first()
    const box = await label.boundingBox()
    expect(box?.width).toBeCloseTo(120, 0)
    await expect(list.getByText('—')).toBeVisible()
  })

  test('VC-C39-01: 脱敏手机号按权限显示', async ({ page }) => {
    await expect(page.locator('.description-list').getByText('138****5678')).toBeVisible()
    await expect(page.locator('.masked-text, .description-list').getByText('138****5678').first()).toBeVisible()
  })

  test('VC-C40-01: 图表配色自适应空数据', async ({ page }) => {
    const chart = page.locator('.chart').first()
    await expect(chart).toBeVisible()
    const box = await chart.boundingBox()
    expect(box?.width).toBeGreaterThan(0)
    expect(box?.height).toBeGreaterThan(0)
    await expect(page.locator('.chart-empty')).toHaveText('暂无数据')
  })

  test('VC-C41-01: 流程画布缩放拖动点击', async ({ page }) => {
    skipOnMobile(page, '手机视口豁免画布缩放')
    const canvas = page.locator('.trace-graph')
    await expect(canvas).toBeVisible()
    await expect(canvas).toHaveAttribute('data-scale', '1')
    await canvas.hover()
    await page.mouse.wheel(0, -120)
    await expect(canvas).toHaveAttribute('data-scale', '1.1')
    await canvas.locator('.graph-node').first().click()
    await expect(page.locator('.node-log')).toContainText('已点击')
  })
})
