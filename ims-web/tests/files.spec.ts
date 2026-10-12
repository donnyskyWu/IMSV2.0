/**
 * 文件组件测试
 * 依据: 02-验证用例.md, FP-C17~C18
 */
import { test, expect } from '@playwright/test'

test.describe('FileUpload 组件 (FP-C17-01)', () => {
  test('应显示上传区域', async ({ page }) => {
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo')
    
    // 应有上传拖拽区
    const uploadDragger = page.locator('.el-upload-dragger, .el-upload')
    await expect(uploadDragger.first()).toBeVisible()
  })
})

test.describe('FilePreview 组件 (FP-C17-02)', () => {
  test('应显示文件预览列表', async ({ page }) => {
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo')
    
    // 应有文件预览区
    const filePreview = page.locator('.file-preview')
    await expect(filePreview).toBeVisible()
    
    // 应有文件项
    const fileItems = filePreview.locator('.file-item')
    const count = await fileItems.count()
    expect(count).toBeGreaterThan(0)
  })
})

test.describe('ImportDialog 组件 (FP-C18-01)', () => {
  test('应能打开导入对话框', async ({ page }) => {
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo')
    
    // 点击打开导入按钮
    const importBtn = page.locator('button:has-text("打开导入")')
    await importBtn.click()
    
    // 对话框应打开
    const dialog = page.locator('.el-dialog')
    await expect(dialog).toBeVisible()
    
    // 应有下载模板按钮
    const templateBtn = dialog.locator('button:has-text("下载")')
    await expect(templateBtn).toBeVisible()
  })
})

test.describe('ExportButton 组件 (FP-C18-02)', () => {
  test('应显示导出下拉菜单', async ({ page }) => {
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo')
    
    // 找到导出按钮部分
    const exportSection = page.locator('.demo-section:has-text("导出按钮")')
    const exportBtn = exportSection.locator('button:has-text("导出")')
    await exportBtn.click()
    
    // 等待下拉菜单出现
    await page.waitForTimeout(300)
    
    // 应显示下拉菜单
    const dropdown = page.locator('.el-dropdown-menu:visible')
    await expect(dropdown).toBeVisible()
    
    // 应有导出选项
    const items = dropdown.locator('.el-dropdown-menu__item')
    const count = await items.count()
    expect(count).toBeGreaterThan(0)
  })
})
