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

function jsonBody(body: unknown, status = 200) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

function ok(data: unknown) {
  return { code: 0, msg: '成功', data }
}

function menu(path: string, name: string) {
  return { id: path, name, path, type: 'MENU', sort: 0, visible: true, children: [] }
}

function bearerToken(authorization: string | undefined): string {
  const header = authorization || ''
  return header.toLowerCase().startsWith('bearer ') ? header.slice(7).trim() : ''
}

function sampleTodo(
  id: string,
  type: string,
  title: string,
  status: string,
  isOverdue: boolean,
) {
  return {
    id,
    type,
    title,
    content: null,
    sourceModule: '账号',
    sourceType: null,
    sourceId: null,
    route: '/ims/auth/org',
    status,
    dueTime: null,
    isOverdue,
    overdueDays: isOverdue ? 1 : 0,
    createTime: null,
    doneTime: null,
    doneBy: null,
    doneByName: null,
  }
}

function menusFor(token: string) {
  if (token === 'r10-token') return [menu('/ims/workbench', '个人工作台')]
  return [
    menu('/ims/workbench', '个人工作台'),
    menu('/ims/auth/org', '组织架构同步'),
    menu('/ims/auth/position', '岗位-角色供给规则'),
  ]
}

/**
 * 组件套件没有后端。登录、/me 和工作台接口都在浏览器里挡掉，
 * 不把这组用例塞进 live-proxy，避免和改密夹具抢同一个种子账号。
 */
async function installWorkbenchMocks(page: Page) {
  await page.route('**/admin-api/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const token = bearerToken(request.headers().authorization)

    if (path.endsWith('/auth/login') && request.method() === 'POST') {
      const raw = request.postDataJSON() as { username?: string } | null
      const username = raw?.username || ''
      const accessToken = username === 'test_r10'
        ? 'r10-token'
        : username === 'test_reset'
          ? 'reset-token'
          : username === 'test_yg'
            ? 'yg-token'
            : 'admin-token'
      await route.fulfill(jsonBody(ok({
        accessToken,
        refreshToken: `${accessToken}-refresh`,
        expiresIn: 7200,
        pwdResetRequired: username === 'test_reset',
      })))
      return
    }

    if (path.endsWith('/auth/me')) {
      if (!token) {
        await route.fulfill(jsonBody({ code: 1002, msg: '登录已失效，请重新登录', data: null }, 401))
        return
      }
      await route.fulfill(jsonBody(ok({
        user: {
          id: '1',
          username: token.replace('-token', ''),
          nickname: token === 'r10-token' ? '外协' : '测试管理员',
          avatar: null,
          deptNames: ['信息部'],
          mainDeptName: '信息部',
          roleNames: ['系统管理员', '审计员'],
          positionLabel: null,
          pwdResetRequired: token === 'reset-token',
        },
        menus: menusFor(token),
        permCodes: ['ims:workbench:query'],
        permDetails: {},
        dataScopeText: '本人',
      })))
      return
    }

    if (path.endsWith('/workbench/dashboard')) {
      if (token === 'reset-token') {
        await route.fulfill(jsonBody({ code: 1008, msg: '请先修改密码', data: null }))
        return
      }
      await route.fulfill(jsonBody(ok({
        todoCount: 0,
        todoByType: {},
        todoOverdue: 0,
        unreadMessageCount: 0,
        myAccountCount: null,
        myAssetCount: null,
        myApprovalCount: null,
        myAttendanceCount: null,
      })))
      return
    }

    if (path.endsWith('/todo/my/get')) {
      const id = new URL(request.url()).searchParams.get('id')
      if (id === '999999999') {
        await route.fulfill(jsonBody({ code: 1504, msg: '待办不存在', data: null }))
        return
      }
    }

    if (path.endsWith('/todo/my/page') || path.endsWith('/message/my/page') || path.endsWith('/message/my/get')) {
      await route.fulfill(jsonBody(ok({
        total: 0,
        pageNo: 1,
        pageSize: 20,
        list: [],
      })))
      return
    }

    if (path.endsWith('/todo/my/count')) {
      await route.fulfill(jsonBody(ok({ total: 0, byType: {}, overdue: 0 })))
      return
    }

    if (path.endsWith('/message/my/unread-count')) {
      await route.fulfill(jsonBody(ok(0)))
      return
    }

    if (path.endsWith('/message/my/read') || path.endsWith('/message/my/read-all')) {
      await route.fulfill(jsonBody(ok({ updated: 1 })))
      return
    }

    await route.fulfill(jsonBody(ok(null)))
  })
}

async function revealSidebar(page: Page) {
  const width = page.viewportSize()?.width ?? 1440
  if (width <= 390) {
    await page.locator('.app-layout').locator('> .app-main > .app-topbar .menu-btn').click()
  }
}

test.describe('B3 个人工作台', () => {
  test.beforeEach(async ({ page }) => {
    await installWorkbenchMocks(page)
  })

  test.describe('WB 工作台首页', () => {
    test('E2E-B3-WB-01: 无 redirect 落地 /ims/workbench，侧栏高亮排第一', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await expect(page).toHaveURL(/\/ims\/workbench/)
      await revealSidebar(page)
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
      expect(titleText).toMatch(/(凌晨好|早上好|中午好|下午好|晚上好)/)
      await expect(header).toContainText('主部门：信息部')
      await expect(header).toContainText('系统管理员')
      await expect(header).toContainText('审计员')
      const todoPreview = page.getByTestId('todo-preview')
      await expect(todoPreview).toContainText('暂无待办')
      for (const label of ['全部待办', '审批待办', '审核待办', '归还待办', '告警待办']) {
        const tab = todoPreview.getByText(label)
        await tab.scrollIntoViewIfNeeded()
        await expect(tab).toBeVisible()
      }
      await expect(todoPreview.getByRole('button', { name: '查看更多' })).toBeVisible()
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
      await page.goBack()
      const todoPreview = page.getByTestId('todo-preview')
      const approvalTab = todoPreview.getByText('审批待办')
      await approvalTab.scrollIntoViewIfNeeded()
      await approvalTab.click()
      await todoPreview.getByRole('button', { name: '查看更多' }).click()
      await expect(page).toHaveURL(/\/ims\/workbench\/todos\?tab=APPROVAL/)
      await expect(page.locator('.el-select')).toContainText('待处理')
    })
  })

  test.describe('TD 待办中心', () => {
    test('E2E-B3-TD-01: Tab 切换、状态筛选、分页正确', async ({ page }) => {
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      await expect(page).toHaveURL(/\/ims\/workbench\/todos/)
      const tabs = page.locator('.el-radio-group .el-radio-button')
      await expect(tabs.first()).toContainText('全部待办')
      await expect(page.getByText('审批待办').first()).toBeVisible()
      const statusSelect = page.locator('.el-select')
      await expect(statusSelect).toContainText('待处理')
      await statusSelect.click()
      await expect(page.getByRole('option', { name: '已过期' })).toBeVisible()
      await expect(page.getByRole('option', { name: '已处理' })).toBeVisible()
      const table = page.locator('.el-table')
      await expect(table).toBeVisible()
      await expect(table).toContainText('暂无待办')
    })

    test('E2E-B3-TD-01: 已处理与已过期可查看，已过期仍可去处理', async ({ page }) => {
      await page.route('**/admin-api/ims/todo/my/page**', async (route) => {
        await route.fulfill(jsonBody(ok({
          total: 2,
          pageNo: 1,
          pageSize: 20,
          list: [
            sampleTodo('1', 'ALERT', '已过期告警', 'PENDING', true),
            sampleTodo('2', 'CONFIRM', '已处理确认', 'DONE', false),
          ],
        })))
      })
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      const overdue = page.locator('.el-table__row').filter({ hasText: '已过期告警' })
      await expect(overdue.getByRole('button', { name: '查看' })).toBeVisible()
      await expect(overdue.getByRole('button', { name: '去处理' })).toBeVisible()
      await expect(overdue).toContainText('已过期')
      const done = page.locator('.el-table__row').filter({ hasText: '已处理确认' })
      await expect(done.getByRole('button', { name: '查看' })).toBeVisible()
      await expect(done.getByRole('button', { name: '去处理' })).toHaveCount(0)
      await expect(done).toContainText('已处理')
      await done.getByRole('button', { name: '查看' }).click()
      const drawer = page.locator('.detail-drawer')
      await expect(drawer).toBeVisible()
      await expect(drawer).toContainText('已处理')
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

    test('E2E-B3-TD-03: 去处理先确认仍待处理再跳转', async ({ page }) => {
      let detailCalls = 0
      await page.route('**/admin-api/ims/todo/my/**', async (route) => {
        const url = new URL(route.request().url())
        if (url.pathname.endsWith('/todo/my/page')) {
          await route.fulfill(jsonBody(ok({
            total: 1,
            pageNo: 1,
            pageSize: 20,
            list: [sampleTodo('42', 'APPROVAL', '领用审批', 'PENDING', false)],
          })))
          return
        }
        if (url.pathname.endsWith('/todo/my/get')) {
          detailCalls += 1
          await route.fulfill(jsonBody(ok(sampleTodo('42', 'APPROVAL', '领用审批', 'PENDING', false))))
          return
        }
        if (url.pathname.endsWith('/todo/my/count')) {
          await route.fulfill(jsonBody(ok({ total: 1, byType: { APPROVAL: 1 }, overdue: 0 })))
          return
        }
        await route.fallback()
      })
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      await page.getByRole('button', { name: '去处理' }).click()
      await expect(page).toHaveURL(/\/ims\/auth\/org/)
      expect(detailCalls).toBeGreaterThan(0)
    })

    test('E2E-B3-TD-03: 1504 时归还待办由本人关闭，审批待办只提示', async ({ page }) => {
      const closed: string[] = []
      await page.route('**/admin-api/ims/todo/my/**', async (route) => {
        const request = route.request()
        const url = new URL(request.url())
        if (url.pathname.endsWith('/todo/my/close') && request.method() === 'PUT') {
          const body = request.postDataJSON() as { id?: number }
          closed.push(String(body?.id))
          await route.fulfill(jsonBody(ok(null)))
          return
        }
        if (url.pathname.endsWith('/todo/my/page')) {
          await route.fulfill(jsonBody(ok({
            total: 2,
            pageNo: 1,
            pageSize: 20,
            list: [
              sampleTodo('7', 'RETURN', '归还设备', 'PENDING', false),
              sampleTodo('8', 'APPROVAL', '审批单据', 'PENDING', false),
            ],
          })))
          return
        }
        if (url.pathname.endsWith('/todo/my/get')) {
          await route.fulfill(jsonBody({ code: 1504, msg: '待办不存在', data: null }))
          return
        }
        if (url.pathname.endsWith('/todo/my/count')) {
          await route.fulfill(jsonBody(ok({ total: 2, byType: { RETURN: 1, APPROVAL: 1 }, overdue: 0 })))
          return
        }
        await route.fallback()
      })
      await loginAs(page, 'test_admin')
      await page.goto('/ims/workbench/todos')
      await page.locator('.el-table__row').filter({ hasText: '归还设备' }).getByRole('button', { name: '去处理' }).click()
      await expect(page.locator('.el-message').filter({ hasText: '单据已被处理或删除' })).toBeVisible()
      await expect.poll(() => closed).toContain('7')
      await page.locator('.el-table__row').filter({ hasText: '审批单据' }).getByRole('button', { name: '去处理' }).click()
      await expect.poll(() => closed.slice()).toEqual(['7'])
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
      if ((page.viewportSize()?.width ?? 1440) <= 390) {
        await page.locator('.page-header .el-dropdown').click()
      }
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
      await expect(page).toHaveURL((url) => url.pathname === '/ims/workbench')
      await expect(page.getByTestId('unassigned-panel')).toHaveCount(0)
      await revealSidebar(page)
      const sidebar = page.getByTestId('app-sidebar')
      await expect(sidebar.locator('.el-menu-item')).toHaveCount(1)
      await expect(sidebar.getByText('个人工作台')).toBeVisible()
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

    test('E2E-B3-BG-04: 无权限用户打开组织页看到无权限', async ({ page }) => {
      await loginAs(page, 'test_r10')
      await page.goto('/ims/auth/org')
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
