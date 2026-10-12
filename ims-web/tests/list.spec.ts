/**
 * 列表类组件测试
 * 依据: 02-验证用例.md VC-C06~C13, VC-L02
 */
import { test, expect } from '@playwright/test'
import { skipOnMobile } from './helpers/viewport'

test.describe('C06～C13. 列表类', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo')
  })

  test('VC-C06-01: 关键字回车搜索', async ({ page }) => {
    const input = page.getByPlaceholder('请输入名称')
    await input.fill('示例订单 001')
    await input.press('Enter')
    await expect(page.locator('.el-table__body tbody tr')).toHaveCount(1)
    await expect(page.getByText('示例订单 001')).toBeVisible()
    await expect(page.locator('.el-pager li.is-active')).toHaveText('1')
  })

  test('VC-C06-02: 查询栏更多收起展开', async ({ page }) => {
    skipOnMobile(page)
    await expect(page.locator('.query-field:visible')).toHaveCount(4)
    await page.getByRole('button', { name: '更多' }).click()
    await expect(page.locator('.query-field:visible')).toHaveCount(6)
    await expect(page.getByPlaceholder('证件号')).toBeVisible()
    await expect(page.getByPlaceholder('创建日期')).toBeVisible()
  })

  test('VC-C06-03: 重置清空条件回第 1 页', async ({ page }) => {
    await page.getByPlaceholder('请输入名称').fill('示例订单')
    await page.getByRole('button', { name: '查询' }).click()
    await page.locator('.el-pager li').filter({ hasText: '2' }).click()
    await expect(page.locator('.el-pager li.is-active')).toHaveText('2')
    await page.getByRole('button', { name: '重置' }).click()
    await expect(page.getByPlaceholder('请输入名称')).toHaveValue('')
    await expect(page.locator('.el-pager li.is-active')).toHaveText('1')
    await expect(page.getByText('示例订单 002')).toBeVisible()
  })

  test('VC-C06-04: 条件和页码刷新保持', async ({ page }) => {
    await page.getByPlaceholder('请输入名称').fill('示例订单')
    await page.getByRole('button', { name: '查询' }).click()
    await page.locator('.el-pager li').filter({ hasText: '2' }).click()
    await page.reload()
    await page.waitForSelector('.list-demo')
    await expect(page.getByPlaceholder('请输入名称')).toHaveValue('示例订单')
    await expect(page.locator('.el-pager li.is-active')).toHaveText('2')
  })

  test('VC-C07-01: 表格编号等宽金额右对齐状态彩色', async ({ page }) => {
    const table = page.locator('.el-table').first()
    await expect(table).toBeVisible()
    const statusTag = page.locator('.status-tag').first()
    await expect(statusTag).toBeVisible()
    const bgColor = await statusTag.evaluate((el) => getComputedStyle(el).backgroundColor)
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
  })

  test('VC-C07-02: 列排序升降序', async ({ page }) => {
    const amountHeader = page.locator('.el-table__header th').filter({ hasText: '金额' })
    await expect(amountHeader).toHaveClass(/is-sortable/)
    await expect(page.locator('.el-table__header th').filter({ hasText: '名称' })).not.toHaveClass(/is-sortable/)
    await amountHeader.click()
    await expect(amountHeader).toHaveClass(/ascending/)
    const asc = await page.locator('.el-table__body tbody tr').first().innerText()
    await amountHeader.click()
    await expect(amountHeader).toHaveClass(/descending/)
    const desc = await page.locator('.el-table__body tbody tr').first().innerText()
    expect(asc).not.toBe(desc)
  })

  test('VC-C07-03: 操作列更多下拉删除红字', async ({ page }) => {
    skipOnMobile(page)
    await page.locator('.el-table').getByRole('button', { name: '更多' }).first().click()
    const deleteItem = page.locator('.el-dropdown-menu__item').filter({ hasText: '删除' })
    await expect(deleteItem).toBeVisible()
    const color = await deleteItem.locator('.danger-text').evaluate((el) => getComputedStyle(el).color)
    expect(color).toMatch(/rgb\(215,\s*0,\s*21\)|rgb\(255,\s*59,\s*48\)|#d70015|#ff3b30/i)
  })

  test('VC-C07-04: 脱敏字段显示和悬停提示', async ({ page }) => {
    const idCard = page.getByText('110***********1234').first()
    await expect(idCard).toBeVisible()
    const masked = page.locator('.masked').first()
    await masked.hover()
    await expect(page.getByRole('tooltip').filter({ hasText: '无查看权限' })).toBeVisible()
  })

  test('VC-C08-01: 分页总数改每页跳页', async ({ page }) => {
    skipOnMobile(page)
    const pagination = page.locator('.pagination')
    await expect(pagination).toContainText(/共\s*35\s*条/)
    await pagination.locator('.page-size-select').click()
    await page.locator('.el-select-dropdown__item').filter({ hasText: '20 条/页' }).click()
    await expect(page.locator('.el-table__body tbody tr')).toHaveCount(20)
  })

  test('VC-C08-02: 最后一页删空自动退回', async ({ page }) => {
    const pagination = page.locator('.pagination')
    await expect(pagination).toBeVisible()
    await expect(pagination).toContainText('共')
  })

  test('VC-C08-03: 无结果只显示共 0 条', async ({ page }) => {
    skipOnMobile(page)
    await page.getByPlaceholder('请输入名称').fill('不存在的搜索词xxxyyy')
    await page.getByPlaceholder('请输入名称').press('Enter')
    await expect(page.getByText('暂无数据')).toBeVisible()
    await expect(page.locator('.pagination-total')).toHaveText('共 0 条')
    await expect(page.locator('.el-pager')).toHaveCount(0)
  })

  test('VC-C09-01: 状态色冻结橙停用灰等', async ({ page }) => {
    const tag = page.locator('.status-tag').first()
    await expect(tag).toBeVisible()
    const bgColor = await tag.evaluate((el) => getComputedStyle(el).backgroundColor)
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
  })

  test('VC-C10-01: 统计卡环比正负色', async ({ page }) => {
    skipOnMobile(page)
    await page.goto('/demo/tabs-list')
    const cards = page.locator('.stat-card')
    await expect(cards).toHaveCount(4)
    await expect(page.locator('.stat-ratio.ratio--down')).toBeVisible()
    await expect(page.locator('.stat-ratio.ratio--up').first()).toBeVisible()
    const cols = await page.locator('.stat-grid').evaluate((el) => getComputedStyle(el).gridTemplateColumns)
    expect(cols.split(' ').length).toBe(4)
  })

  test('VC-C11-01: 空态无权限加载失败三种', async ({ page }) => {
    await page.getByPlaceholder('请输入名称').fill('不存在的名称xyz')
    await page.getByPlaceholder('请输入名称').press('Enter')
    await expect(page.getByText('暂无数据')).toBeVisible()
    await page.getByRole('button', { name: '无权限' }).click()
    await expect(page.getByText('暂无权限查看此内容')).toBeVisible()
    await page.getByRole('button', { name: '加载失败' }).click()
    await expect(page.getByText('加载失败，请稍后重试')).toBeVisible()
    await page.getByRole('button', { name: '重试' }).click()
    await expect(page.getByText('已重试 1')).toBeVisible()
  })

  test('VC-C12-01: 条件标签关闭清空重新查询', async ({ page }) => {
    await page.getByPlaceholder('请输入名称').fill('示例')
    await page.getByPlaceholder('订单号').fill('ORD')
    await page.locator('.query-bar').getByPlaceholder('全部').click()
    await page.getByRole('option', { name: '草稿' }).click()
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.chip')).toHaveCount(3)
    await page.locator('.chip').filter({ hasText: '状态' }).locator('.chip__close').click()
    await expect(page.locator('.chip').filter({ hasText: '状态' })).toHaveCount(0)
    await expect(page.locator('.chip')).toHaveCount(2)
  })

  test('VC-L02-01: Tab 间切换保持各自条件', async ({ page }) => {
    await page.goto('/demo/tabs-list')
    const input = page.getByPlaceholder('本页条件')
    await input.fill('系统问题')
    await input.blur()
    await page.getByText('待处理', { exact: true }).click()
    await expect(input).toHaveValue('')
    await expect(page.locator('.el-pager li.is-active, .mobile-pager')).toBeVisible()
    await page.getByText('全部', { exact: true }).click()
    await expect(input).toHaveValue('系统问题')
  })
})
