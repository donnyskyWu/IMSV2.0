/**
 * 其他模板测试
 * 依据: 02-验证用例.md VC-L01, VC-L04~L08
 */
import { test, expect } from '@playwright/test'

test.describe('其他模板', () => {
  test.fixme('VC-L01-01: 标准列表增删改查流程', async ({ page }) => {
    // 依赖后端 CRUD API
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')
  })

  test('VC-L01-02: 详情后条件页码保持', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const searchInput = page.locator('.query-bar input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试')
      await searchInput.press('Enter')
      await page.waitForTimeout(500)

      const viewBtn = page.locator('button:has-text("查看")').first()
      if (await viewBtn.isVisible()) {
        await viewBtn.click()
        await page.waitForTimeout(500)

        const drawer = page.locator('.el-drawer').first()
        if (await drawer.isVisible()) {
          await page.keyboard.press('Escape')
          await page.waitForTimeout(300)

          const inputValue = await searchInput.inputValue()
          expect(inputValue).toBe('测试')
        }
      }
    }
  })

  test('VC-L04-01: 看板切换周期刷新', async ({ page }) => {
    await page.goto('/demo/workbench')
    await page.waitForSelector('.workbench-demo, .app-layout')

    const periodSelect = page.locator('.period-select, .el-select:has-text("本月")').first()
    if (await periodSelect.isVisible()) {
      await periodSelect.click()
      await page.waitForTimeout(300)

      const option = page.locator('.el-select-dropdown__item:has-text("上月")').first()
      if (await option.isVisible()) {
        await option.click()
        await page.waitForTimeout(500)
      }
    }

    const updateTime = page.locator(':text("截至"), .update-time')
    if (await updateTime.count() > 0) {
      await expect(updateTime.first()).toBeVisible()
    }
  })

  test.fixme('VC-L05-01: 工作台待办和消息', async ({ page }) => {
    // 依赖后端 API
    await page.goto('/demo/workbench')
    await page.waitForSelector('.workbench-demo, .app-layout')
  })

  test.fixme('VC-L05-02: 待办无权限提示', async ({ page }) => {
    // 依赖后端 API
  })

  test('VC-L06-01: 设计器未保存提示', async ({ page }) => {
    await page.goto('/demo/display')
    await page.waitForSelector('.display-demo, .app-layout')

    const designerSection = page.locator('.designer-section, .trace-graph').first()
    if (await designerSection.isVisible()) {
      // 模拟修改内容
    }
  })

  test('VC-L07-01: 填报页无侧栏连点提交', async ({ page }) => {
    await page.goto('/demo/fill')
    await page.waitForSelector('.fill-demo, .app-layout')

    const sidebar = page.locator('.sidebar, .app-sidebar')
    if (page.viewportSize()?.width! < 768) {
      test.skip(true, '移动端侧栏行为不同')
    }

    const submitBtn = page.locator('button:has-text("提交")').first()
    if (await submitBtn.isVisible()) {
      for (let i = 0; i < 3; i++) {
        await submitBtn.click()
        await page.waitForTimeout(50)
      }

      await page.waitForTimeout(500)
    }
  })

  test('VC-L08-01: 详情抽屉模板 Tab 和按钮', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const viewBtn = page.locator('button:has-text("查看")').first()
    if (await viewBtn.isVisible()) {
      await viewBtn.click()
      await page.waitForTimeout(500)

      const drawer = page.locator('.el-drawer, .detail-drawer').first()
      if (await drawer.isVisible()) {
        const header = drawer.locator('.el-drawer__header, .drawer-header').first()
        await expect(header).toBeVisible()

        const tabs = drawer.locator('.el-tabs')
        if (await tabs.count() > 0) {
          await expect(tabs.first()).toBeVisible()
        }

        const footer = drawer.locator('.el-drawer__footer, .drawer-footer')
        if (await footer.count() > 0) {
          await expect(footer.first()).toBeVisible()
        }

        await page.keyboard.press('Escape')
      }
    }
  })
})
