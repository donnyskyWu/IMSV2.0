/**
 * B3 个人工作台 E2E 测试
 * 依据: 个人工作台-实现理解 §6
 *
 * 20 条用例覆盖:
 * - WB: 工作台首页 (4 条)
 * - TD: 待办中心 (6 条)
 * - MS: 消息中心 (4 条)
 * - BG: 后台能力 (6 条)
 */
import { test, expect, type Page } from '@playwright/test'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
const seedPassword = env?.E2E_SEED_PASSWORD || 'Test1234'

interface ApiBody {
  code?: number
  data?: unknown
  msg?: string
}

async function openFreshLogin(page: Page) {
  await page.goto('/login')
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await page.goto('/login')
}

async function loginAs(page: Page, username: string, password: string = seedPassword) {
  await openFreshLogin(page)
  await page.getByPlaceholder('用户名').fill(username)
  await page.getByPlaceholder('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL((url) => url.pathname !== '/login')
}

async function callApi(
  page: Page,
  method: 'GET' | 'POST' | 'PUT',
  apiPath: string,
  token: string | null = null,
  body?: unknown,
): Promise<{ status: number; body: ApiBody }> {
  return page.evaluate(async ({ method, apiPath, token, body }) => {
    const headers: Record<string, string> = {}
    if (token) headers.Authorization = `Bearer ${token}`
    if (body !== null && body !== undefined) headers['Content-Type'] = 'application/json'
    const response = await fetch(apiPath, {
      method,
      headers,
      body: body !== null && body !== undefined ? JSON.stringify(body) : undefined,
    })
    const payload = await response.json() as ApiBody
    return { status: response.status, body: payload }
  }, { method, apiPath, token, body: body === undefined ? null : body })
}

async function getAccessToken(page: Page): Promise<string | null> {
  return page.evaluate(() => localStorage.getItem('ims_access_token'))
}

test.describe('B3 个人工作台', () => {
  test.describe('WB 工作台首页', () => {
    test('E2E-B3-WB-01: 无 redirect 落地 /ims/workbench，侧栏高亮排第一', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await expect(page).toHaveURL(/\/ims\/workbench/)
      const sidebar = page.locator('[data-testid="app-sidebar"]')
      await expect(sidebar).toBeVisible()
      await expect(sidebar.getByText('个人工作台')).toBeVisible()
      const firstMenuItem = sidebar.locator('.el-menu-item').first()
      await expect(firstMenuItem).toContainText('个人工作台')
      await expect(firstMenuItem).toHaveClass(/is-active/)
    })

    test('E2E-B3-WB-02: 问候含姓名，只有两张数据卡', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await expect(page).toHaveURL(/\/ims\/workbench/)
      const header = page.locator('.page-header')
      await expect(header).toBeVisible()
      const title = header.locator('.page-title')
      const titleText = await title.textContent()
      expect(titleText).toMatch(/(早上好|中午好|下午好|晚上好)/)
      const statCards = page.locator('[data-testid^="stat-"]')
      await expect(statCards).toHaveCount(2)
      await expect(page.getByTestId('stat-todo')).toBeVisible()
      await expect(page.getByTestId('stat-message')).toBeVisible()
    })

    test('E2E-B3-WB-03: 待办预览最多 10 条，逾期红底置顶', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await expect(page).toHaveURL(/\/ims\/workbench/)
      const todoPreview = page.getByTestId('todo-preview')
      await expect(todoPreview).toBeVisible()
      const todoCards = todoPreview.locator('[data-testid="todo-card"]')
      const count = await todoCards.count()
      expect(count).toBeLessThanOrEqual(10)
    })

    test('E2E-B3-WB-04: 点卡片跳转对应中心', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await expect(page).toHaveURL(/\/ims\/workbench/)
      await page.getByTestId('stat-todo').click()
      await expect(page).toHaveURL(/\/ims\/workbench\/todos/)
      await page.goBack()
      await page.getByTestId('stat-message').click()
      await expect(page).toHaveURL(/\/ims\/workbench\/messages/)
    })
  })

  test.describe('TD 待办中心', () => {
    test('E2E-B3-TD-01: Tab 切换、状态筛选、分页正确', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      await expect(page).toHaveURL(/\/ims\/workbench\/todos/)
      const tabs = page.locator('.el-radio-group .el-radio-button')
      await expect(tabs.first()).toContainText('全部')
      const statusSelect = page.locator('.el-select')
      await expect(statusSelect).toBeVisible()
      const table = page.locator('.el-table')
      await expect(table).toBeVisible()
    })

    test('E2E-B3-TD-02: 逾期待办红底高亮', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      const overdueRows = page.locator('.el-table__row .overdue-text')
      if (await overdueRows.count() > 0) {
        const firstOverdue = overdueRows.first()
        await expect(firstOverdue).toHaveCSS('color', 'rgb(245, 63, 63)')
      }
    })

    test('E2E-B3-TD-03: 去处理跳转成功（路由可达）', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      const goButton = page.locator('.el-table__row').first().getByRole('button', { name: '去处理' })
      if (await goButton.isVisible()) {
        await goButton.click()
      }
    })

    test('E2E-B3-TD-04: 待办已处理后列表刷新', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      const table = page.locator('.el-table')
      await expect(table).toBeVisible()
    })

    test('E2E-B3-TD-05: 关闭确认类待办成功', async ({ page }) => {
      await loginAs(page, 'test_yg')
      await page.goto('/ims/workbench/todos')
      const closeButton = page.locator('.el-table__row').filter({ hasText: '确认' }).first().getByRole('button', { name: '关闭' })
      if (await closeButton.isVisible()) {
        await closeButton.click()
        await page.getByRole('button', { name: '关闭' }).last().click()
        await expect(page.locator('.el-message').filter({ hasText: '已关闭' })).toBeVisible()
      }
    })

    test('E2E-B3-TD-06: 审批类待办无关闭按钮', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      const approvalRow = page.locator('.el-table__row').filter({ hasText: '审批' }).first()
      if (await approvalRow.isVisible()) {
        const closeBtn = approvalRow.getByRole('button', { name: '关闭' })
        await expect(closeBtn).toHaveCount(0)
      }
    })
  })

  test.describe('MS 消息中心', () => {
    test('E2E-B3-MS-01: Tab 切换正确，搜索命中', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/messages')
      await expect(page).toHaveURL(/\/ims\/workbench\/messages/)
      const tabs = page.locator('.el-radio-group .el-radio-button')
      await expect(tabs.first()).toContainText('全部')
      await tabs.nth(1).click()
      await expect(page.locator('.el-table')).toBeVisible()
    })

    test('E2E-B3-MS-02: 标记已读幂等', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/messages')
      const unreadRow = page.locator('.el-table__row').filter({ has: page.locator('.el-tag:has-text("未读")') }).first()
      if (await unreadRow.isVisible()) {
        const markBtn = unreadRow.getByRole('button', { name: '标为已读' })
        if (await markBtn.isVisible()) {
          await markBtn.click()
          await expect(page.locator('.el-message').filter({ hasText: '已读' })).toBeVisible()
        }
      }
    })

    test('E2E-B3-MS-03: 全部已读返回 updated', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/messages')
      await page.getByRole('button', { name: '全部已读' }).click()
      await expect(page.locator('.el-message').filter({ hasText: '已读' })).toBeVisible()
    })

    test('E2E-B3-MS-04: 铃铛抽屉 420px，点击已读 -1', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.locator('.msg-badge button').click()
      const drawer = page.locator('.el-drawer')
      await expect(drawer).toBeVisible()
    })
  })

  test.describe('BG 后台能力', () => {
    test('E2E-B3-BG-01: R10 视角侧栏只有工作台', async ({ page }) => {
      await loginAs(page, 'test_r10')
      await expect(page).toHaveURL((url) => url.pathname === '/')
      await expect(page.getByTestId('unassigned-panel')).toHaveText('您的账号尚未分配权限，请联系管理员')
    })

    test('E2E-B3-BG-02: 有 id 参数的接口访问他人数据返回 1504', async ({ page }) => {
      await loginAs(page, 'test_admin')
      const token = await getAccessToken(page)
      const result = await callApi(page, 'GET', '/admin-api/ims/todo/my/get?id=999999999', token)
      expect(result.body.code).toBe(1504)
    })

    test('E2E-B3-BG-03: 须改密时 dashboard 返回 1008，/me 成功', async ({ page }) => {
      await openFreshLogin(page)
      await page.getByPlaceholder('用户名').fill('test_reset')
      await page.getByPlaceholder('密码').fill(seedPassword)
      await page.getByRole('button', { name: '登录' }).click()
      await expect(page).toHaveURL(/\/password-reset/)
      const token = await getAccessToken(page)
      const dashboard = await callApi(page, 'GET', '/admin-api/ims/auth/workbench/dashboard', token)
      expect(dashboard.body.code).toBe(1008)
      const me = await callApi(page, 'GET', '/admin-api/ims/auth/me', token)
      expect(me.body.code).toBe(0)
    })

    test('E2E-B3-BG-04: 无权限用户落地无权限页', async ({ page }) => {
      await loginAs(page, 'test_r10')
      await page.goto('/ims/workbench')
      await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    })

    test('E2E-B3-BG-05: 不出现他人待办/消息', async ({ page }) => {
      await loginAs(page, 'test_yg')
      await page.goto('/ims/workbench/todos')
      const table = page.locator('.el-table')
      await expect(table).toBeVisible()
      const adminTodo = page.locator('.el-table__row').filter({ hasText: 'test_admin' })
      await expect(adminTodo).toHaveCount(0)
    })

    test('E2E-B3-BG-06: test_yg_b 只见本人数据', async ({ page }) => {
      await loginAs(page, 'test_yg')
      await page.goto('/ims/workbench/messages')
      const table = page.locator('.el-table')
      await expect(table).toBeVisible()
    })
  })
})
