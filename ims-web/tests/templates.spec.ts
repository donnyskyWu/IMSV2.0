/**
 * 其他模板测试
 * 依据: 02-验证用例.md VC-L01, VC-L04~L08
 */
import { test, expect } from '@playwright/test'
import { isNarrow, skipOnMobile } from './helpers/viewport'

test.describe('其他模板', () => {
  test('VC-L01-01: 标准列表增删改查流程', async ({ page }) => {
    await page.goto('/demo/list')
    await expect(page.locator('.el-table')).toBeVisible()
    await expect(page.getByRole('button', { name: '新建' }).first()).toBeVisible()
    if (isNarrow(page)) {
      await page.locator('.list-demo .el-table').getByRole('button', { name: '更多' }).first().click()
      await expect(page.locator('.el-dropdown-menu:visible').getByText('编辑', { exact: true })).toBeVisible()
      await page.keyboard.press('Escape')
    } else {
      await expect(page.getByRole('button', { name: '编辑' }).first()).toBeVisible()
    }
    await page.getByRole('button', { name: '新建' }).first().click()
    const drawer = page.locator('.el-drawer:visible')
    await drawer.getByPlaceholder('请输入名称').fill('标准新增')
    await drawer.getByRole('button', { name: '保存' }).click()
    await expect(page.getByText('标准新增')).toBeVisible()
    await expect(page.locator('.el-message').filter({ hasText: '保存成功' })).toBeVisible()
  })

  test('VC-L01-02: 详情后条件页码保持', async ({ page }) => {
    await page.goto('/demo/list')
    const searchInput = page.getByPlaceholder('请输入名称')
    await searchInput.fill('示例订单')
    await page.getByRole('button', { name: '查询' }).click()
    if (isNarrow(page)) {
      await page.locator('.list-demo .el-table').getByRole('button', { name: '更多' }).first().click()
      await page.locator('.el-dropdown-menu:visible').getByText('查看', { exact: true }).click()
    } else {
      await page.getByRole('button', { name: '查看' }).first().click()
    }
    await expect(page.locator('.el-drawer:visible')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('.el-drawer:visible')).toHaveCount(0)
    await expect(searchInput).toHaveValue('示例订单')
    await expect(page.getByRole('cell', { name: '示例订单 002' })).toBeVisible()
  })

  test('VC-L04-01: 看板切换周期刷新', async ({ page }) => {
    await page.goto('/demo/workbench')
    await expect(page.locator('.update-time')).toContainText('截至 2026-10-12 10:00')
    await page.locator('.period-select').click()
    await page.getByRole('option', { name: '上月' }).click()
    await expect(page.locator('.update-time')).toContainText('截至 2026-09-30 23:59')
  })

  test('VC-L05-01: 工作台待办和消息', async ({ page }) => {
    await page.goto('/demo/workbench')
    await expect(page.getByText('审批 2')).toBeVisible()
    await expect(page.getByText('预警 1')).toBeVisible()
    await expect(page.getByText('未读消息 3')).toBeVisible()
    await page.getByRole('button', { name: '审批单甲' }).click()
    await expect(page).toHaveURL(/#todo/)
  })

  test('VC-L05-02: 待办无权限提示', async ({ page }) => {
    await page.goto('/demo/workbench')
    await page.getByText('预警 1').click()
    await page.getByRole('button', { name: '库存预警' }).click()
    await expect(page.getByText('暂无权限')).toBeVisible()
    await expect(page).not.toHaveURL(/#todo/)
  })

  test('VC-L06-01: 设计器未保存提示', async ({ page }) => {
    skipOnMobile(page, '手机下设计器只读，无法修改')
    await page.goto('/demo/display')
    await page.getByPlaceholder('修改设计内容').fill('改了一处')
    const blocked = await page.evaluate(() => {
      const event = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(event)
      return event.defaultPrevented
    })
    expect(blocked).toBe(true)
    await page.getByRole('menuitem', { name: '列表演示' }).first().click()
    await expect(page.getByText('有未保存修改')).toBeVisible()
    await expect(page).toHaveURL(/\/demo\/display/)
  })

  test('VC-L07-01: 填报页无侧栏连点提交', async ({ page }) => {
    await page.goto('/demo/fill')
    await expect(page.locator('.app-sidebar')).toHaveCount(0)
    await expect(page.locator('.app-topbar')).toBeVisible()
    const submit = page.getByRole('button', { name: '提交' })
    await submit.click()
    await submit.click({ force: true })
    await submit.click({ force: true })
    await expect(page.getByText('已提交 1')).toBeVisible()
    await expect(page.locator('.el-message').filter({ hasText: '提交成功' })).toHaveCount(1)
  })

  test('VC-L08-01: 详情抽屉模板 Tab 和按钮', async ({ page }) => {
    await page.goto('/demo/list')
    if (isNarrow(page)) {
      await page.locator('.list-demo .el-table').getByRole('button', { name: '更多' }).first().click()
      await page.locator('.el-dropdown-menu:visible').getByText('查看', { exact: true }).click()
    } else {
      await page.getByRole('button', { name: '查看' }).first().click()
    }
    const drawer = page.locator('.el-drawer:visible')
    await expect(drawer.locator('.el-drawer__header').first()).toBeVisible()
    await expect(drawer.getByRole('tab', { name: '基本信息' })).toBeVisible()
    await expect(drawer.getByRole('tab', { name: '操作记录' })).toBeVisible()
    await expect(drawer.getByRole('button', { name: '关闭', exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(drawer).toBeHidden()
  })
})
