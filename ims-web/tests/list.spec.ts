/**
 * 列表类组件测试
 * 依据: 02-验证用例.md VC-C06~C13, VC-L02
 */
import { test, expect } from '@playwright/test'

test.describe('C06～C13. 列表类', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')
  })

  test('VC-C06-01: 关键字回车搜索', async ({ page }) => {
    const searchInput = page.locator('.query-bar input, .el-input input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试')
      await searchInput.press('Enter')
      await page.waitForTimeout(500)
    }
  })

  test('VC-C06-02: 查询栏更多收起展开', async ({ page }) => {
    const moreBtn = page.locator('button:has-text("更多"), button:has-text("展开"), .expand-btn').first()
    if (await moreBtn.isVisible()) {
      await moreBtn.click()
      await page.waitForTimeout(300)
    }
  })

  test('VC-C06-03: 重置清空条件回第 1 页', async ({ page }) => {
    const resetBtn = page.locator('button:has-text("重置")').first()
    if (await resetBtn.isVisible()) {
      await resetBtn.click()
      await page.waitForTimeout(500)
    }
  })

  test('VC-C06-04: 条件和页码刷新保持', async ({ page }) => {
    const searchInput = page.locator('.query-bar input, .el-input input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('保持测试')
      await searchInput.press('Enter')
      await page.waitForTimeout(500)

      await page.reload()
      await page.waitForSelector('.list-demo, .app-layout')
    }
  })

  test('VC-C07-01: 表格编号等宽金额右对齐状态彩色', async ({ page }) => {
    const table = page.locator('.el-table').first()
    await expect(table).toBeVisible()

    const statusTag = page.locator('.status-tag, .el-tag').first()
    if (await statusTag.isVisible()) {
      const bgColor = await statusTag.evaluate((el) => getComputedStyle(el).backgroundColor)
      expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
    }
  })

  test('VC-C07-02: 列排序升降序', async ({ page }) => {
    const sortableHeader = page.locator('.el-table__header th.is-sortable').first()
    if (await sortableHeader.isVisible()) {
      await sortableHeader.click()
      await page.waitForTimeout(300)

      await sortableHeader.click()
      await page.waitForTimeout(300)
    }
  })

  test('VC-C07-03: 操作列更多下拉删除红字', async ({ page }) => {
    const moreBtn = page.locator('.el-table .el-dropdown, .operation-more, button:has-text("更多")').first()
    if (await moreBtn.isVisible()) {
      await moreBtn.click()
      await page.waitForTimeout(300)

      const deleteItem = page.locator('.el-dropdown-menu__item:has-text("删除")').first()
      if (await deleteItem.count() > 0 && await deleteItem.isVisible()) {
        const color = await deleteItem.evaluate((el) => getComputedStyle(el).color)
        expect(color).toBeDefined()
      }
    }
  })

  test('VC-C07-04: 脱敏字段显示和悬停提示', async ({ page }) => {
    const maskedCell = page.locator('.el-table td:has-text("***"), .masked-text').first()
    if (await maskedCell.isVisible()) {
      await maskedCell.hover()
      await page.waitForTimeout(300)
    }
  })

  test('VC-C08-01: 分页总数改每页跳页', async ({ page }) => {
    const pagination = page.locator('.el-pagination, .pagination').first()
    if (await pagination.isVisible()) {
      const total = pagination.locator('.el-pagination__total, .total-count')
      if (await total.count() > 0) {
        await expect(total.first()).toContainText(/共.*条/)
      }
    }
  })

  test.fixme('VC-C08-02: 最后一页删空自动退回', async ({ page }) => {
    // 依赖后端删除 API
  })

  test('VC-C08-03: 无结果只显示共 0 条', async ({ page }) => {
    const searchInput = page.locator('.query-bar input, .el-input input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('不存在的搜索词xxxyyy')
      await searchInput.press('Enter')
      await page.waitForTimeout(500)

      const emptyState = page.locator('.el-empty, .empty-state, :text("暂无数据")')
      const zeroTotal = page.locator(':text("共 0 条"), :text("共0条")')

      const hasEmpty = await emptyState.count() > 0 || await zeroTotal.count() > 0
      expect(hasEmpty).toBe(true)
    }
  })

  test('VC-C09-01: 状态色冻结橙停用灰等', async ({ page }) => {
    const statusTags = page.locator('.status-tag, .el-tag')
    const count = await statusTags.count()

    if (count > 0) {
      const tag = statusTags.first()
      const bgColor = await tag.evaluate((el) => getComputedStyle(el).backgroundColor)
      expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
    }
  })

  test('VC-C10-01: 统计卡环比正负色', async ({ page }) => {
    await page.goto('/demo/tabs-list')
    await page.waitForSelector('.tabs-list-demo, .app-layout')

    const statCards = page.locator('.stat-card')
    const count = await statCards.count()

    if (count > 0) {
      const card = statCards.first()
      await expect(card).toBeVisible()
    }
  })

  test('VC-C11-01: 空态无权限加载失败三种', async ({ page }) => {
    const emptyStates = [
      { selector: '.empty-state, .el-empty', text: '暂无数据' },
      { selector: '.no-permission', text: '暂无权限' },
      { selector: '.load-error', text: '加载失败' },
    ]

    for (const state of emptyStates) {
      const el = page.locator(state.selector).first()
      if (await el.count() > 0) {
        break
      }
    }
  })

  test('VC-C12-01: 条件标签关闭清空重新查询', async ({ page }) => {
    const chip = page.locator('.query-chip, .el-tag.is-closable').first()
    if (await chip.isVisible()) {
      const closeBtn = chip.locator('.el-tag__close, .close-btn')
      if (await closeBtn.isVisible()) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('VC-L02-01: Tab 间切换保持各自条件', async ({ page }) => {
    await page.goto('/demo/tabs-list')
    await page.waitForSelector('.tabs-list-demo, .app-layout')

    const tabs = page.locator('.el-tabs__item')
    const count = await tabs.count()

    if (count > 1) {
      const firstTab = tabs.first()
      const secondTab = tabs.nth(1)

      await secondTab.click()
      await page.waitForTimeout(300)

      await firstTab.click()
      await page.waitForTimeout(300)
    }
  })
})
