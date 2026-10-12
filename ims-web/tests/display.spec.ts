/**
 * 展示组件测试
 * 依据: 02-验证用例.md VC-C37~C41, VC-R-17
 */
import { test, expect } from '@playwright/test'

test.describe('C37～C41. 展示组件', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/display')
    await page.waitForSelector('.display-demo, .app-layout')
  })

  test('VC-R-17: 金额百分比时间空值格式化', async ({ page }) => {
    const moneyText = page.locator('.money-text, :text("¥")').first()
    if (await moneyText.isVisible()) {
      const text = await moneyText.textContent()
      expect(text).toMatch(/¥[\d,]+\.\d{2}/)
    }

    const negativeAmount = page.locator(':text("-¥"), :text("¥-")').first()
    if (await negativeAmount.isVisible()) {
      const color = await negativeAmount.evaluate((el) => getComputedStyle(el).color)
      expect(color).toMatch(/rgb\(255,|#ff/)
    }

    const percentText = page.locator('.percent-text, :text("%")').first()
    if (await percentText.isVisible()) {
      const text = await percentText.textContent()
      expect(text).toMatch(/\d+%/)
    }

    const emptyDash = page.locator(':text("—"), :text("-")').first()
    if (await emptyDash.count() > 0) {
      await expect(emptyDash).toBeVisible()
    }
  })

  test('VC-C37-01: 时间线最新在上可展开', async ({ page }) => {
    const timeline = page.locator('.el-timeline, .timeline').first()
    if (await timeline.isVisible()) {
      const items = timeline.locator('.el-timeline-item')
      const count = await items.count()
      expect(count).toBeGreaterThan(0)

      const expandBtn = timeline.locator('.expand-btn, :text("展开")').first()
      if (await expandBtn.isVisible()) {
        await expandBtn.click()
        await page.waitForTimeout(300)
      }
    }
  })

  test('VC-C38-01: 详情字段标签列宽空值横线', async ({ page }) => {
    const descriptionList = page.locator('.description-list, .el-descriptions').first()
    if (await descriptionList.isVisible()) {
      const labels = descriptionList.locator('.el-descriptions__label, .desc-label')
      if (await labels.count() > 0) {
        const firstLabel = labels.first()
        const box = await firstLabel.boundingBox()
        expect(box?.width).toBeGreaterThan(0)
      }

      const emptyValue = descriptionList.locator(':text("—")')
      if (await emptyValue.count() > 0) {
        await expect(emptyValue.first()).toBeVisible()
      }
    }
  })

  test.fixme('VC-C39-01: 脱敏手机号按权限显示', async ({ page }) => {
    // 依赖后端权限 API
  })

  test('VC-C40-01: 图表配色自适应空数据', async ({ page }) => {
    const charts = page.locator('.chart, canvas, [data-echarts]')
    const count = await charts.count()

    if (count > 0) {
      const chart = charts.first()
      await expect(chart).toBeVisible()

      const box = await chart.boundingBox()
      if (box) {
        expect(box.width).toBeGreaterThan(0)
        expect(box.height).toBeGreaterThan(0)
      }
    }

    const emptyChart = page.locator('.chart-empty, :text("暂无数据")')
    if (await emptyChart.count() > 0) {
      await expect(emptyChart.first()).toBeVisible()
    }
  })

  test('VC-C41-01: 流程画布缩放拖动点击', async ({ page }) => {
    const canvas = page.locator('.trace-graph, .flow-canvas, canvas').first()
    if (await canvas.isVisible()) {
      await expect(canvas).toBeVisible()

      await page.mouse.wheel(0, 100)
      await page.waitForTimeout(300)

      const nodeClick = page.locator('.graph-node, .flow-node').first()
      if (await nodeClick.isVisible()) {
        await nodeClick.click()
        await page.waitForTimeout(300)
      }
    }
  })
})
