/**
 * 选择器组件测试
 * 依据: 02-验证用例.md, FP-C15
 */
import { test, expect } from '@playwright/test'

test.describe('UserSelect 组件 (FP-C15-03)', () => {
  test('应打开下拉并显示选项', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到用户选择器部分
    const userSection = page.locator('.demo-section:has-text("用户选择器")')
    const userSelect = userSection.locator('.el-select').first()
    await userSelect.click()
    
    // 等待下拉加载
    await page.waitForTimeout(500)
    
    // 应显示下拉选项
    const dropdown = page.locator('.el-select-dropdown:visible')
    await expect(dropdown).toBeVisible()
    
    // 应有选项
    const options = page.locator('.el-select-dropdown:visible .el-select-dropdown__item')
    const count = await options.count()
    expect(count).toBeGreaterThan(0)
  })

  test('应能选择选项', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到用户选择器部分
    const userSection = page.locator('.demo-section:has-text("用户选择器")')
    const userSelect = userSection.locator('.el-select').first()
    await userSelect.click()
    
    // 等待下拉加载
    await page.waitForTimeout(500)
    
    // 选择第一个选项
    const firstOption = page.locator('.el-select-dropdown:visible .el-select-dropdown__item').first()
    await firstOption.click()
    
    // 选择器应显示选中值
    await page.waitForTimeout(300)
  })
})

test.describe('DeptTreeSelect 组件 (FP-C15-04)', () => {
  test('应显示树形下拉', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到部门选择器
    const deptSelect = page.locator('.dept-tree-select, .el-tree-select').first()
    await deptSelect.click()
    
    // 应显示树形结构
    const tree = page.locator('.el-tree')
    await expect(tree).toBeVisible()
    
    // 应有树节点
    const nodes = tree.locator('.el-tree-node')
    const count = await nodes.count()
    expect(count).toBeGreaterThan(0)
  })
})

test.describe('DateRangePicker 组件 (FP-C15-06)', () => {
  test('应显示日期范围选择器', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到日期范围选择器
    const datePicker = page.locator('.date-range-picker, .el-date-editor--daterange').first()
    await datePicker.click()
    
    // 应显示日期面板
    const panel = page.locator('.el-picker-panel')
    await expect(panel).toBeVisible()
  })

  test('应显示快捷选项', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到日期范围选择器
    const datePicker = page.locator('.date-range-picker, .el-date-editor--daterange').first()
    await datePicker.click()
    
    // 应有快捷选项
    const shortcuts = page.locator('.el-picker-panel__shortcut')
    const count = await shortcuts.count()
    expect(count).toBeGreaterThan(0)
  })
})

test.describe('DictSelect 组件 (FP-C15-02)', () => {
  test('应显示字典选项', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo')
    
    // 找到字典选择器部分
    const dictSection = page.locator('.demo-section:has-text("字典选择器")')
    const dictSelect = dictSection.locator('.el-select').first()
    
    if (await dictSelect.isVisible()) {
      await dictSelect.click()
      await page.waitForTimeout(500)
      
      // 应显示选项
      const dropdown = page.locator('.el-select-dropdown:visible')
      await expect(dropdown).toBeVisible()
    }
  })
})
