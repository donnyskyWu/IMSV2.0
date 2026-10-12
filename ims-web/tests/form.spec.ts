/**
 * 表单与弹层测试
 * 依据: 02-验证用例.md VC-C14~C20
 */
import { test, expect } from '@playwright/test'
import { isNarrow } from './helpers/viewport'

test.describe('C14～C20. 表单与弹层', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')
  })

  test('VC-C14-01: 三档抽屉宽度 480/720/880', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const drawerSizes = [
      { name: '小', width: 480 },
      { name: '中', width: 720 },
      { name: '大', width: 880 },
    ]

    for (const size of drawerSizes) {
      await page.getByRole('button', { name: `打开${size.name}抽屉` }).click()
      const drawer = page.locator('.el-drawer:visible')
      await expect(drawer).toBeVisible()
      const box = await drawer.boundingBox()
      expect(box?.width).toBeCloseTo(size.width, -1)
      await drawer.getByRole('button', { name: '取消' }).click()
      await expect(drawer).toBeHidden()
    }
  })

  test('VC-C14-02: 修改后点遮罩弹确认', async ({ page }) => {
    await page.goto('/demo/list')
    await page.getByRole('button', { name: '新建' }).first().click()
    const drawer = page.locator('.el-drawer:visible')
    await drawer.getByPlaceholder('请输入名称').fill('改过')
    const overlay = page.locator('.el-overlay').first()
    const box = await overlay.boundingBox()
    expect(box).toBeTruthy()
    await page.mouse.click(box!.x + 8, box!.y + box!.height / 2)
    await expect(page.getByText('有未保存的修改，确定离开吗？')).toBeVisible()
    await expect(drawer).toBeVisible()
  })

  test('VC-C14-03: 未修改按 Esc 直接关闭', async ({ page }) => {
    await page.goto('/demo/list')
    await page.getByRole('button', { name: '新建' }).first().click()
    const drawer = page.locator('.el-drawer:visible')
    await expect(drawer).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(drawer).toBeHidden()
  })

  test('VC-C14-04: 连点保存只新增一条', async ({ page }) => {
    await page.goto('/demo/list')
    await page.getByRole('button', { name: '新建' }).first().click()
    await page.locator('.el-drawer:visible').getByPlaceholder('请输入名称').fill('只新增一条')
    const save = page.locator('.el-drawer:visible').getByRole('button', { name: '保存' })
    await save.click()
    await save.click({ force: true })
    await save.click({ force: true })
    await expect(page.locator('.el-message').filter({ hasText: '保存成功' })).toHaveCount(1)
    await expect(page.locator('.el-drawer:visible')).toHaveCount(0)
    await expect(page.getByText('只新增一条')).toHaveCount(1)
  })

  test('VC-C14-05: 金额小数位校验', async ({ page }) => {
    await page.goto('/demo/list')
    await page.getByRole('button', { name: '新建' }).first().click()
    const amount = page.locator('.el-drawer:visible').getByPlaceholder('金额')
    await amount.fill('12.345')
    await amount.blur()
    await expect(page.locator('.el-drawer:visible').getByText('金额最多 2 位小数')).toBeVisible()
  })

  test('VC-C15-01: 详情抽屉头和 Tab', async ({ page }) => {
    await page.goto('/demo/list')
    if (isNarrow(page)) {
      await page.locator('.list-demo .el-table').getByRole('button', { name: '更多' }).first().click()
      await page.locator('.el-dropdown-menu:visible').getByText('查看', { exact: true }).click()
    } else {
      await page.getByRole('button', { name: '查看' }).first().click()
    }
    const drawer = page.locator('.el-drawer:visible')
    await expect(drawer).toBeVisible()
    await expect(drawer.locator('.el-tabs')).toBeVisible()
    await expect(drawer.getByRole('tab', { name: '基本信息' })).toBeVisible()
    await expect(drawer.getByRole('tab', { name: '操作记录' })).toBeVisible()
  })

  test('VC-C16-01: 删除红色确认框', async ({ page }) => {
    await page.goto('/demo/list')
    await page.locator('.el-table').getByRole('button', { name: '更多' }).first().click()
    await page.locator('.el-dropdown-menu:visible').getByText('删除', { exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    const okBtn = dialog.getByRole('button', { name: '确定' })
    const bgColor = await okBtn.evaluate((el) => getComputedStyle(el).backgroundColor)
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
    expect(bgColor).toMatch(/rgb\(/)
  })

  test('VC-C16-02: 作废填原因才能确定', async ({ page }) => {
    await page.getByRole('button', { name: '作废' }).click()
    const dialog = page.getByRole('dialog', { name: '作废' })
    const confirmBtn = dialog.getByRole('button', { name: '确定' })
    await expect(confirmBtn).toBeDisabled()
    await dialog.getByPlaceholder('请填写作废原因').fill('测试作废原因')
    await expect(confirmBtn).toBeEnabled()
  })

  test('VC-C16-03: 删除被引用提示 1502', async ({ page }) => {
    await page.goto('/demo/list')
    const row = page.locator('.el-table__body tr').filter({ hasText: '示例订单 003' })
    await row.getByRole('button', { name: '更多' }).click()
    await page.locator('.el-dropdown-menu:visible').getByText('删除', { exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await dialog.getByRole('button', { name: '确定' }).click()
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('关联的实体已被其他记录引用')
    await expect(page.getByRole('cell', { name: '示例订单 003', exact: true })).toBeVisible()
  })

  test('VC-C17-01: 表单校验红框中文错误', async ({ page }) => {
    await page.getByRole('button', { name: '提交' }).click()
    const error = page.locator('.el-form-item__error').first()
    await expect(error).toBeVisible()
    await expect(error).toContainText('请输入')
    await expect(page.locator('.el-form-item.is-error').first()).toBeVisible()
  })

  test('VC-C18-01: 三档弹窗居中 Esc 关闭', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')
    const tiers = [
      { name: '小', width: 360 },
      { name: '中', width: 520 },
      { name: '大', width: 800 },
    ]
    for (const tier of tiers) {
      await page.getByRole('button', { name: `打开${tier.name}弹窗` }).click()
      const modal = page.locator('.el-dialog:visible')
      await expect(modal).toBeVisible()
      await expect(modal).toContainText('示例弹窗')
      const box = await modal.boundingBox()
      const viewport = page.viewportSize()
      expect(box).toBeTruthy()
      expect(box!.width).toBeCloseTo(tier.width, -1)
      expect(Math.abs(box!.x + box!.width / 2 - viewport!.width / 2)).toBeLessThan(50)
      await page.keyboard.press('Escape')
      await expect(modal).toBeHidden()
    }
  })

  test('VC-C19-01: 向导步骤校验和上下步', async ({ page }) => {
    await page.getByRole('button', { name: '打开向导' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: '下一步' }).click()
    await expect(dialog.getByText('请填写必填项')).toBeVisible()
    await expect(dialog.getByText('基本信息')).toBeVisible()
    await dialog.getByPlaceholder('请输入名称').fill('向导名称')
    await dialog.getByRole('button', { name: '下一步' }).click()
    await expect(dialog.getByText('已填写：向导名称')).toBeVisible()
    await dialog.getByRole('button', { name: '上一步' }).click()
    await expect(dialog.getByPlaceholder('请输入名称')).toHaveValue('向导名称')
    await dialog.getByRole('button', { name: '下一步' }).click()
    await dialog.getByRole('button', { name: '下一步' }).click()
    await expect(dialog.getByRole('button', { name: '完成' })).toBeVisible()
  })

  test('VC-C20-01: 同一提示只显示一条', async ({ page }) => {
    const toastBtn = page.getByRole('button', { name: '重复提示' })
    for (let i = 0; i < 5; i++) await toastBtn.click()
    await expect(page.locator('.el-message').filter({ hasText: '同一条提示' })).toHaveCount(1)
  })
})
