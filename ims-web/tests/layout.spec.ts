/**
 * 布局与导航测试
 * 依据: 02-验证用例.md VC-C01~C05
 */
import { test, expect } from '@playwright/test'

test.describe('C01～C05. 布局与导航', () => {
  test('VC-C01-01: 侧栏菜单应按权限显示且高亮当前', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    await page.goto('/demo/layout')
    const sidebar = page.locator('.app-sidebar').last()
    await expect(sidebar).toBeVisible()
    await expect(sidebar.getByText('布局演示')).toBeVisible()
    await expect(sidebar.locator('.el-menu-item.is-active')).toContainText('布局演示')
  })

  test('VC-C01-02: 不同账号侧栏菜单应不同', async ({ page }) => {
    await page.goto('/demo/layout')
    const items = page.locator('.el-menu-item')
    await expect(items.filter({ hasText: '部门树' })).toHaveCount(2)
    await expect(items.filter({ hasText: '布局演示' })).toHaveCount(2)
    await page.evaluate(() => {
      localStorage.removeItem('ims_access_token')
      localStorage.removeItem('ims_refresh_token')
      sessionStorage.setItem('ims_menu_profile', 'narrow')
    })
    await page.reload()
    await expect(page.locator('.el-menu-item').filter({ hasText: '列表演示' })).toHaveCount(2)
    await expect(page.locator('.el-menu-item').filter({ hasText: '部门树' })).toHaveCount(0)
    await expect(page.locator('.el-menu-item').filter({ hasText: '布局演示' })).toHaveCount(0)
  })

  test('VC-C01-03: 顶栏铃铛和头像下拉', async ({ page }) => {
    await page.goto('/demo/layout')
    const topbar = page.locator('.app-topbar').first()
    await expect(topbar).toBeVisible()
    await expect(topbar.locator('.el-icon').first()).toBeVisible()
    await topbar.locator('.user-dropdown').click()
    await expect(page.locator('.el-dropdown-menu:visible').getByText('退出登录').first()).toBeVisible()
  })

  test('VC-C01-04: 侧栏折叠状态持久化', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    await page.goto('/demo/layout')
    await page.locator('.menu-btn').first().click()
    await expect(page.locator('.app-layout').first()).toHaveClass(/sidebar-collapsed/)
    await page.reload()
    await expect(page.locator('.app-layout').first()).toHaveClass(/sidebar-collapsed/)
  })

  test('VC-C02-01: 页头应显示统计范围', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    await page.goto('/demo/layout')
    await expect(page.locator('.page-header').getByText('统计范围：全部')).toBeVisible()
  })

  test('VC-C03-01: Tab 切换和刷新状态持久化', async ({ page }) => {
    await page.goto('/demo/layout')
    const tab = page.locator('.tab-item').filter({ hasText: '标签二' }).first()
    await expect(tab).toBeVisible()
    await tab.click()
    await expect(tab).toHaveClass(/active/)
    await page.reload()
    await expect(page.locator('.tab-item').filter({ hasText: '标签二' }).first()).toHaveClass(/active/)
  })

  test('VC-C04-01: 面包屑折叠和点击', async ({ page }) => {
    await page.goto('/demo/layout')
    const breadcrumb = page.locator('.breadcrumb-demo')
    await expect(breadcrumb).toBeVisible()
    await expect(breadcrumb.getByText('系统管理')).toHaveCount(0)
    await breadcrumb.locator('.crumb-ellipsis').click()
    for (const label of ['首页', '系统管理', '组织架构', '部门管理', '市场部', '市场一组', '详情']) {
      await expect(breadcrumb.getByText(label, { exact: true })).toBeVisible()
    }
  })

  test('VC-C05-01: 权限按钮按角色显示或隐藏', async ({ page }) => {
    await page.goto('/demo/layout')
    const section = page.locator('.perm-demo')
    await expect(section.getByRole('button', { name: '新建 (有权限)' })).toBeVisible()
    await expect(section.getByRole('button', { name: '删除 (有权限)' })).toBeVisible()
    await expect(section.getByRole('button', { name: '超级管理 (无权限，不显示)' })).toHaveCount(0)
  })
})
