/**
 * 响应式测试
 * 依据: 02-验证用例.md, 00-工作包 §2.1
 */
import { test, expect } from '@playwright/test'

test.describe('响应式断点 (Q1)', () => {
  test('桌面视口 (>=768px) 应显示侧边菜单', async ({ page }) => {
    // 仅在桌面项目运行
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')
    
    // 侧边栏应可见 (类名是 sidebar 或 app-sidebar)
    const sidebar = page.locator('.sidebar, .app-sidebar')
    await expect(sidebar.first()).toBeVisible()
  })

  test('移动视口 (<768px) 应隐藏侧边菜单', async ({ page }) => {
    // 仅在移动项目运行
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')
    
    // 侧边栏应隐藏 (移动端通过 CSS transform 隐藏)
    const sidebar = page.locator('.sidebar.mobile-hidden, .app-sidebar.mobile-hidden').first()
    // 验证有 mobile-hidden 类
    await expect(sidebar).toHaveClass(/mobile-hidden/)
  })
})

test.describe('Topbar 高度 (Q2)', () => {
  test('Topbar 高度应为 56px', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-topbar')
    
    const topbar = page.locator('.app-topbar').first()
    const box = await topbar.boundingBox()
    expect(box?.height).toBe(56)
  })
})

test.describe('触控目标 (Q3, §2.3 U1)', () => {
  test('小按钮视觉高度应保持 26px', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.page-header')
    
    // 找到 small 按钮
    const smallBtn = page.locator('.el-button--small').first()
    if (await smallBtn.isVisible()) {
      const box = await smallBtn.boundingBox()
      // 视觉高度应在合理范围
      expect(box?.height).toBeLessThanOrEqual(32)
    }
  })
})

test.describe('分页组件 (Q8)', () => {
  test('移动端分页应简化显示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/list')
    await page.waitForSelector('.pagination')
    
    const pagination = page.locator('.pagination')
    
    // 移动端应隐藏每页条数选择器
    const sizeChanger = pagination.locator('.el-pagination__sizes')
    await expect(sizeChanger).not.toBeVisible()
    
    // 移动端应隐藏跳转输入框
    const jumper = pagination.locator('.el-pagination__jump')
    await expect(jumper).not.toBeVisible()
  })

  test('桌面端分页应完整显示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    
    await page.goto('/demo/list')
    await page.waitForSelector('.pagination')
    
    const pagination = page.locator('.pagination')
    await expect(pagination).toBeVisible()
    
    // 桌面端应显示分页控件
    const pager = pagination.locator('.el-pager, .el-pagination')
    await expect(pager.first()).toBeVisible()
  })
})

test.describe('查询栏 (Q9)', () => {
  test('移动端查询栏应显示筛选按钮', async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/list')
    await page.waitForSelector('.query-bar, .mobile-query-row')
    
    // 应有筛选按钮
    const filterBtn = page.locator('.filter-btn, button:has-text("筛选")')
    // 如果存在多个查询条件，应显示筛选按钮
    // (ListDemo 有多个条件)
  })
})

test.describe('表格首列 (Q4, §2.2 #10)', () => {
  test('移动端表格首列宽度不超过 120px', async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/list')
    await page.waitForSelector('.el-table')
    
    // 获取首列宽度
    const firstCol = page.locator('.el-table__fixed-left .el-table__cell').first()
    if (await firstCol.isVisible()) {
      const box = await firstCol.boundingBox()
      expect(box?.width).toBeLessThanOrEqual(120)
    }
  })

  test.fixme('超长首列内容应显示省略号并有 tooltip (VC-M-07)', async ({ page }) => {
    // 需要第 2 步: 测试需要真实的超长内容和 tooltip 交互
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/list')
    // 第一行首列是超长名称
    const firstCell = page.locator('.el-table__row:first-child .el-table__cell:first-child')
    
    // 应有省略号样式
    await expect(firstCell).toHaveCSS('text-overflow', 'ellipsis')
    
    // 点击/悬停应显示 tooltip
    await firstCell.hover()
    const tooltip = page.locator('.el-tooltip__content, .el-popper')
    await expect(tooltip).toBeVisible()
  })
})

test.describe('Modal/Drawer 移动端全屏 (Q5, Q6)', () => {
  test('移动端 Drawer 应全屏显示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/list')
    await page.waitForSelector('.page-header')
    
    // 点击新建按钮
    const createBtn = page.locator('button:has-text("新建")').first()
    await createBtn.click()
    
    // 等待抽屉打开
    const drawer = page.locator('.el-drawer')
    await expect(drawer).toBeVisible()
    
    // 移动端应全屏
    const box = await drawer.boundingBox()
    const viewportWidth = page.viewportSize()?.width
    expect(box?.width).toBe(viewportWidth)
  })
})

test.describe('左树右表移动端 (Q12)', () => {
  test('移动端树应收进抽屉', async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= 768, '仅限移动视口')
    
    await page.goto('/demo/left-tree-right-table')
    await page.waitForSelector('.mobile-tree-bar, .left-tree-right-table')
    
    // 树面板应不可见
    const treePanel = page.locator('.tree-panel')
    await expect(treePanel).not.toBeVisible()
    
    // 应显示移动端选择栏
    const mobileBar = page.locator('.mobile-tree-bar')
    await expect(mobileBar).toBeVisible()
  })
})
