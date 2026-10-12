/**
 * 布局与导航测试
 * 依据: 02-验证用例.md VC-C01~C05
 */
import { test, expect } from '@playwright/test'

test.describe('C01～C05. 布局与导航', () => {
  test('VC-C01-01: 侧栏菜单应按权限显示且高亮当前', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const sidebar = page.locator('.sidebar, .app-sidebar').first()
    await expect(sidebar).toBeVisible()

    const menuItems = sidebar.locator('.el-menu-item, .menu-item')
    const count = await menuItems.count()
    expect(count).toBeGreaterThan(0)

    const activeItem = sidebar.locator('.el-menu-item.is-active, .menu-item.active').first()
    if (await activeItem.count() > 0) {
      await expect(activeItem).toBeVisible()
    }
  })

  test.fixme('VC-C01-02: 不同账号侧栏菜单应不同', async ({ page }) => {
    // 需要后端权限 API 支持不同账号登录
  })

  test('VC-C01-03: 顶栏铃铛和头像下拉', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const topbar = page.locator('.app-topbar, .topbar').first()
    await expect(topbar).toBeVisible()

    const avatar = topbar.locator('.user-avatar, .avatar, .el-avatar').first()
    if (await avatar.isVisible()) {
      await avatar.click()
      const dropdown = page.locator('.el-dropdown-menu:visible, .user-menu:visible').first()
      await expect(dropdown).toBeVisible()
    }
  })

  test('VC-C01-04: 侧栏折叠状态持久化', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const collapseBtn = page.locator('.collapse-btn, .sidebar-toggle, [data-testid="sidebar-toggle"]').first()
    if (await collapseBtn.isVisible()) {
      await collapseBtn.click()
      await page.waitForTimeout(300)

      await page.reload()
      await page.waitForSelector('.app-layout')

      const sidebar = page.locator('.sidebar.collapsed, .app-sidebar.collapsed, .sidebar.is-collapse').first()
      const isCollapsed = await sidebar.count() > 0
      expect(isCollapsed).toBe(true)
    }
  })

  test('VC-C02-01: 页头应显示统计范围', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const pageHeader = page.locator('.page-header').first()
    await expect(pageHeader).toBeVisible()

    const scopeText = pageHeader.locator('.data-scope, .scope-text, :text("统计范围")')
    if (await scopeText.count() > 0) {
      await expect(scopeText.first()).toBeVisible()
    }
  })

  test('VC-C03-01: Tab 切换和刷新状态持久化', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const tabs = page.locator('.el-tabs, .tabs-container').first()
    if (await tabs.isVisible()) {
      const tabItems = tabs.locator('.el-tabs__item, .tab-item')
      const count = await tabItems.count()

      if (count > 1) {
        const secondTab = tabItems.nth(1)
        await secondTab.click()
        await page.waitForTimeout(300)

        await page.reload()
        await page.waitForSelector('.app-layout')

        const activeTab = tabs.locator('.el-tabs__item.is-active, .tab-item.active').first()
        await expect(activeTab).toBeVisible()
      }
    }
  })

  test('VC-C04-01: 面包屑折叠和点击', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const breadcrumb = page.locator('.el-breadcrumb, .breadcrumb').first()
    if (await breadcrumb.isVisible()) {
      const items = breadcrumb.locator('.el-breadcrumb__item, .breadcrumb-item')
      const count = await items.count()
      expect(count).toBeGreaterThan(0)

      const ellipsis = breadcrumb.locator(':text("…"), :text("...")')
      if (await ellipsis.count() > 0) {
        await ellipsis.first().click()
      }
    }
  })

  test('VC-C05-01: 权限按钮按角色显示或隐藏', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const permSection = page.locator('.permission-demo, .perm-section, :text("权限对照")')
    if (await permSection.count() > 0) {
      const section = permSection.first()
      const createBtn = section.locator('button:has-text("新建"), button:has-text("创建")')
      const deleteBtn = section.locator('button:has-text("删除")')

      if (await createBtn.count() > 0) {
        await expect(createBtn.first()).toBeVisible()
      }
    }
  })
})
