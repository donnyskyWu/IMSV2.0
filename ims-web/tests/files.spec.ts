/**
 * 文件组件测试
 * 依据: 02-验证用例.md VC-C33~C36
 */
import { test, expect } from '@playwright/test'

test.describe('C33～C36. 文件组件', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo, .app-layout')
  })

  test('VC-C33-01: 文件格式前端拦截', async ({ page }) => {
    await page.locator('.limit-100 input[type="file"]').setInputFiles({
      name: 'test.exe',
      mimeType: 'application/x-msdownload',
      buffer: Buffer.from('fake exe content'),
    })
    await expect(page.locator('.el-message').filter({ hasText: '文件格式不支持' })).toBeVisible()
    await expect(page.getByText('test.exe')).toHaveCount(0)
  })

  test('VC-C33-02: 文件大小前端拦截', async ({ page }) => {
    let uploads = 0
    await page.route('**/admin-api/**', async (route) => {
      if (route.request().method() !== 'GET') uploads += 1
      await route.continue()
    })
    await page.locator('.limit-100 input[type="file"]').setInputFiles({
      name: 'large.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('not-really-100mb'),
    })
    await page.locator('.limit-100 input[type="file"]').evaluate((input) => {
      const file = new File(['x'], 'large.pdf', { type: 'application/pdf' })
      Object.defineProperty(file, 'size', { value: 101 * 1024 * 1024 })
      const transfer = new DataTransfer()
      transfer.items.add(file)
      const target = input as HTMLInputElement
      target.files = transfer.files
      target.dispatchEvent(new Event('change', { bubbles: true }))
    })
    await expect(page.locator('.el-message').filter({ hasText: '文件不能超过 100 MB' })).toBeVisible()
    expect(uploads).toBe(0)
  })

  test('VC-C33-03: 伪造格式后端拦截', async ({ page }) => {
    await page.route('**/admin-api/ims/file/check', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1001, msg: '文件格式与扩展名不符' }),
      })
    })
    await page.getByRole('button', { name: '校验伪造格式' }).click()
    await expect(page.locator('.el-message').filter({ hasText: '文件格式与扩展名不符' })).toBeVisible()
  })

  test('VC-C33-04: 上传进度条和预览删除', async ({ page }) => {
    await page.locator('.limit-100 input[type="file"]').setInputFiles({
      name: 'preview.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4'),
    })
    const item = page.locator('.el-upload-list__item').filter({ hasText: 'preview.pdf' })
    await expect(item).toBeVisible()
    await expect(item.locator('.el-progress, .el-icon--upload-success, .el-icon--close').first()).toBeVisible()
    await item.hover()
    await item.locator('.el-icon--close').click()
    await expect(page.getByText('preview.pdf')).toHaveCount(0)
  })

  test('VC-C34-01: 图片页内预览 PDF 新标签', async ({ page }) => {
    const popupPromise = page.waitForEvent('popup')
    await page.getByText('合同文档.pdf').click()
    const popup = await popupPromise
    await expect(popup).toHaveURL(/contract\.pdf/)
    await popup.close()
    await page.getByText('产品图片.jpg').click()
    await expect(page.locator('.el-dialog .preview-image')).toBeVisible()
  })

  test('VC-C34-02: 跨租户文件不可用', async ({ page }) => {
    await page.getByText('跨租户合同.pdf').click()
    await expect(page.getByText('文件不可用')).toBeVisible()
  })

  test('VC-C35-01: 导入错误表显示行号列', async ({ page }) => {
    await page.getByRole('button', { name: '打开导入对话框' }).click()
    const dialog = page.locator('.el-dialog, .el-overlay').last()
    await dialog.locator('input[type="file"]').setInputFiles({
      name: 'bad-import.xlsx',
      mimeType: 'application/vnd.ms-excel',
      buffer: Buffer.from('bad'),
    })
    await page.getByRole('button', { name: '开始导入' }).click()
    await expect(page.getByText('成功 8 行')).toBeVisible()
    await expect(page.getByText('错误 2 行')).toBeVisible()
    await expect(page.locator('.el-table__body').getByRole('cell', { name: '3', exact: true })).toBeVisible()
    await expect(page.locator('.el-table__body').getByRole('cell', { name: '金额', exact: true })).toBeVisible()
    await expect(page.getByText('金额格式错误')).toBeVisible()
    await expect(page.getByRole('button', { name: '确认导入' })).toBeDisabled()
    await expect(page.getByText('列表 0 条')).toBeVisible()
  })

  test('VC-C35-02: 导入成功后列表刷新', async ({ page }) => {
    await page.getByRole('button', { name: '打开导入对话框' }).click()
    await page.locator('.el-dialog input[type="file"]').setInputFiles({
      name: 'ok-import.xlsx',
      mimeType: 'application/vnd.ms-excel',
      buffer: Buffer.from('ok'),
    })
    await page.getByRole('button', { name: '开始导入' }).click()
    await expect(page.getByRole('button', { name: '确认导入' })).toBeEnabled()
    await page.getByRole('button', { name: '确认导入' }).click()
    await expect(page.getByText('列表 10 条')).toBeVisible()
  })

  test('VC-C36-01: 导出下载条跨页面', async ({ page }) => {
    await page.getByRole('button', { name: '导出', exact: true }).click()
    await expect(page.locator('.el-message').filter({ hasText: '已开始导出' })).toBeVisible()
    await expect(page.locator('.download-bar').first()).toBeVisible()
    await page.locator('.el-sub-menu__title').filter({ hasText: '示例' }).last().click()
    await page.getByRole('menuitem', { name: '列表演示' }).last().click()
    await expect(page).toHaveURL(/\/demo\/list/)
    await expect(page.locator('.download-bar').first()).toBeVisible()
    await expect(page.locator('.download-bar').first()).toContainText('订单数据导出.xlsx')
  })

  test('VC-C36-02: 导出失败下载条显示原因', async ({ page }) => {
    await page.getByRole('button', { name: '导出失败' }).click()
    const bar = page.locator('.download-bar').first()
    await expect(bar).toBeVisible()
    await expect(bar).toContainText('失败')
    await expect(bar).toContainText('导出服务暂不可用')
  })
})
