/**
 * B1 账号登录与强制改密（前端）
 * 可跑用例对接 B0a 登录 /me /logout 契约，用 mock 固定响应。
 * 锁定、冻结/离职、改密落库在 live-proxy.spec.ts 里打真实后端。
 * LG-23 的页面部分在本文件用 mock；外协登录在 live-proxy 里跑。
 * 组织事件 1008 仍 skip，等组织同步接口。
 */
import { test, expect, type Page, type Route } from '@playwright/test'
import { expectNoHOverflow } from './helpers/mobile'

const BIG_USER_ID = '9007199254740993'

function json(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

function ok(data: unknown) {
  return { code: 0, msg: '成功', data }
}

function fail(code: number, msg: string, data: unknown = null) {
  return { code, msg, data }
}

function menu(path: string, name: string) {
  return {
    id: path,
    name,
    path,
    type: 'MENU',
    sort: 0,
    visible: true,
    children: [],
  }
}

function mePayload(options?: {
  id?: string
  menus?: ReturnType<typeof menu>[]
  permCodes?: string[]
  pwdResetRequired?: boolean
}) {
  return ok({
    user: {
      id: options?.id ?? '1',
      username: 'test_admin',
      nickname: '测试管理员',
      avatar: null,
      deptNames: ['信息部'],
      mainDeptName: '信息部',
      positionLabel: null,
      pwdResetRequired: options?.pwdResetRequired ?? false,
    },
    menus: options?.menus ?? [menu('/demo/tokens', 'Token 演示')],
    permCodes: options?.permCodes ?? ['ims:demo:order:query'],
    permDetails: {},
    dataScopeText: '全部',
  })
}

async function fulfillLogin(route: Route, body: unknown) {
  await route.fulfill(json(body))
}

async function installAuth(page: Page, login: (route: Route) => Promise<void>) {
  await page.route('**/admin-api/ims/auth/login', login)
  await page.route('**/admin-api/ims/auth/me', async (route) => {
    const authorization = route.request().headers().authorization || ''
    const token = authorization.toLowerCase().startsWith('bearer ')
      ? authorization.slice(7).trim()
      : ''
    // 未登录与后端 #17 一致：HTTP 401 + code 1002。
    if (!token) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify(fail(1002, '登录已失效，请重新登录')),
      })
      return
    }
    await route.fulfill(json(mePayload()))
  })
  await page.route('**/admin-api/ims/auth/logout', async (route) => {
    await route.fulfill(json(ok(null)))
  })
}

async function submitLogin(page: Page, username: string, password: string) {
  await page.getByPlaceholder('请输入用户名').fill(username)
  await page.getByPlaceholder('请输入密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
}

test.describe('B1 账号登录与改密', () => {
  test('登录页只显示账号登录，桌面卡片 400 且手机不横向溢出', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'IMS 内部管理系统' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '登录' })).toBeVisible()
    await expect(page.getByText('遇到问题请联系系统管理员')).toBeVisible()
    await expect(page.getByRole('tab')).toHaveCount(0)
    await expect(page.getByText('钉钉扫码')).toHaveCount(0)

    const width = page.viewportSize()?.width ?? 1440
    const card = page.getByTestId('login-card')
    const box = await card.boundingBox()
    expect(box).not.toBeNull()
    const labelBox = await page.locator('.login-card .el-form-item__label').first().boundingBox()
    const inputBox = await page.getByPlaceholder('请输入用户名').boundingBox()
    expect(labelBox).not.toBeNull()
    expect(inputBox).not.toBeNull()
    expect(labelBox!.y + labelBox!.height).toBeLessThanOrEqual(inputBox!.y + 1)
    if (width <= 390) {
      await expectNoHOverflow(page, 390)
      expect(box!.width).toBeLessThanOrEqual(390)
      expect(box!.x).toBeGreaterThanOrEqual(0)
      const button = await page.getByRole('button', { name: '登录' }).boundingBox()
      expect(button!.height).toBeGreaterThanOrEqual(44)
      const fontSize = await page.getByPlaceholder('请输入用户名').evaluate((el) => getComputedStyle(el).fontSize)
      expect(Number.parseFloat(fontSize)).toBeGreaterThanOrEqual(16)
    } else {
      expect(box!.width).toBeCloseTo(400, 0)
    }
  })

  test('E2E-B1-LG-04 空表单不发起登录，错误密码与不存在用户提示相同', async ({ page }) => {
    let calls = 0
    await installAuth(page, async (route) => {
      calls += 1
      const body = route.request().postDataJSON() as { username: string; password: string }
      expect(body.captcha).toBeUndefined()
      await fulfillLogin(route, fail(1214, '用户名或密码错误'))
    })
    await page.goto('/login')
    await page.getByRole('button', { name: '登录' }).click()
    await expect(page.getByText('请输入用户名')).toBeVisible()
    await expect(page.getByText('请输入密码')).toBeVisible()
    expect(calls).toBe(0)

    await submitLogin(page, 'test_yg', 'Wrong1234')
    await expect(page.getByText('用户名或密码错误')).toBeVisible()
    await expect(page.getByPlaceholder('请输入密码')).toHaveValue('')
    await expect(page.locator('.el-message')).toHaveCount(0)

    await submitLogin(page, 'nobody_x', 'Test1234')
    await expect(page.getByText('用户名或密码错误')).toHaveCount(1)
    await expect(page.getByPlaceholder('请输入密码')).toHaveValue('')
    expect(calls).toBe(2)
    await expect(page).toHaveURL(/\/login/)
  })

  test('用户名去首尾空格后按 B0a 登录成功并记住账号方式', async ({ page }) => {
    await installAuth(page, async (route) => {
      const body = route.request().postDataJSON() as { username: string; password: string }
      expect(body.username).toBe('test_admin')
      expect(body.password).toBe('Test1234')
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.goto('/login')
    await page.getByPlaceholder('请输入密码').press('Enter')
    await expect(page.getByText('请输入用户名')).toBeVisible()

    await page.getByPlaceholder('请输入用户名').fill('  test_admin  ')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByPlaceholder('请输入密码').press('Enter')
    await expect(page).toHaveURL(/\/demo\/tokens/)
    await expect(page.evaluate(() => localStorage.getItem('ims_last_login_method'))).resolves.toBe('password')
    await expect(page.evaluate(() => localStorage.getItem('ims_access_token'))).resolves.toBe('access-1')
  })

  test('E2E-B1-LG-03 外站 redirect 被忽略并进入第一个菜单', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [menu('/demo/tokens', 'Token 演示'), menu('/demo/list', '列表演示')],
      })))
    })
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.goto('/login?redirect=https://www.baidu.com')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page).toHaveURL(/\/demo\/tokens$/)
    expect(page.url()).not.toContain('baidu')
  })

  test('E2E-B1-LG-02 菜单内 redirect 登录后回到原页', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [menu('/demo/tokens', 'Token 演示'), menu('/demo/list', '列表演示')],
      })))
    })
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.goto('/login?redirect=/demo/list')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page).toHaveURL(/\/demo\/list/)
  })

  test('不在菜单中的站内 redirect 改落到第一个已登记菜单', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [menu('/demo/tokens', 'Token 演示'), menu('/demo/list', '列表演示')],
      })))
    })
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.goto('/login?redirect=/demo/form')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page).toHaveURL(/\/demo\/tokens$/)
  })

  test('E2E-B1-LG-12 已登录访问登录页进入系统，退出后后退仍停在登录页', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        id: BIG_USER_ID,
        menus: [menu('/not-registered', '未登记'), menu('/demo/layout', '布局演示')],
      })))
    })
    // 不用 addInitScript：它会在每次跳转前把令牌写回去，后退用例就失真了。
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('ims_access_token', 'already')
      localStorage.setItem('ims_refresh_token', 'already-r')
    })
    await page.goto('/login?redirect=https://www.baidu.com')
    await expect(page).toHaveURL(/\/demo\/layout/)
    expect(page.url()).not.toContain('baidu')
    await expect(page.locator('.app-layout').first()).toBeVisible()
    await expect(page.getByText('布局演示').first()).toBeVisible()

    // 布局演示页里还有一层示例框架，只点最外层顶栏的头像。
    await page.locator('.app-layout').first().locator('> .app-main > .app-topbar .user-dropdown').click()
    await page.locator('.el-dropdown-menu:visible').getByRole('menuitem', { name: '退出登录' }).click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByPlaceholder('请输入用户名')).toBeVisible()
    await expect(page.locator('.app-layout')).toHaveCount(0)
    await expect(page.evaluate(() => localStorage.getItem('ims_access_token'))).resolves.toBeNull()

    await page.goBack()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByPlaceholder('请输入用户名')).toBeVisible()
    await expect(page.locator('.app-layout')).toHaveCount(0)
    await expect(page.getByText('布局演示')).toHaveCount(0)
    await expect(page.evaluate(() => localStorage.getItem('ims_access_token'))).resolves.toBeNull()
  })

  test('用户 id 按字符串保留，超长数字不被改写', async ({ page }) => {
    await installAuth(page, async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.unroute('**/admin-api/ims/auth/me')
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        id: BIG_USER_ID,
        menus: [menu('/not-a-page', '未登记页面')],
        permCodes: ['ims:demo:order:query'],
      })))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/')
    await expect(page.locator('.app-layout')).toHaveAttribute('data-user-id', BIG_USER_ID)
    await expect(page.getByTestId('unassigned-panel')).toContainText('您的账号尚未分配权限，请联系管理员')
  })

  test('E2E-B1-LG-09 无角色用户停在内容区未分配权限提示', async ({ page }) => {
    await installAuth(page, async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.unroute('**/admin-api/ims/auth/me')
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({ menus: [], permCodes: [] })))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_norole', 'Test1234')
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/')
    await expect(page.getByTestId('unassigned-panel')).toHaveText('您的账号尚未分配权限，请联系管理员')
    await expect(page.locator('.app-sidebar .el-menu-item')).toHaveCount(0)
    await expect(page.locator('.no-menu-tip')).toHaveCount(0)
    await page.goto('/ims/auth/org')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    await expect(page.locator('.el-table, .org-page')).toHaveCount(0)
    await expect(page.locator('.no-menu-tip')).toHaveText('您的账号尚未分配权限，请联系管理员')
  })

  test('已登记的组织与岗位叶子可点并跳转，未登记的部门管理不画', async ({ page }) => {
    await installAuth(page, async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.unroute('**/admin-api/ims/auth/me')
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [
          menu('/ims/auth/org', '组织架构同步'),
          menu('/ims/auth/position', '岗位-角色供给规则'),
          menu('/system/dept', '部门管理'),
        ],
        permCodes: ['ims:system:org-sync:query', 'ims:auth:position-rule:query'],
      })))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/ims/auth/org')
    await expect(page.getByTestId('b1-page-title')).toHaveText('组织架构同步')
    await expect(page.getByTestId('denied-panel')).toHaveCount(0)

    const sidebar = page.locator('.app-sidebar')
    await expect(sidebar.locator('.el-menu-item')).toHaveCount(2)
    await expect(sidebar.getByText('组织架构同步')).toHaveCount(1)
    await expect(sidebar.getByText('岗位-角色供给规则')).toHaveCount(1)
    await expect(sidebar.getByText('部门管理')).toHaveCount(0)

    const width = page.viewportSize()?.width ?? 1440
    if (width <= 390) {
      await page.locator('.app-layout').first().locator('> .app-main > .app-topbar .menu-btn').click()
    }
    await sidebar.getByRole('menuitem', { name: '岗位-角色供给规则' }).click()
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/ims/auth/position')
    await expect(page.getByTestId('b1-page-title')).toHaveText('岗位-角色供给规则')
    await expect(page.getByTestId('denied-panel')).toHaveCount(0)
    await expect(page.locator('.el-table')).toHaveCount(0)
  })

  test('E2E-B1-LG-23 仅工作台菜单落地 /ims/workbench', async ({ page }) => {
    await installAuth(page, async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'r10-token',
        refreshToken: 'r10-refresh',
        expiresIn: 7200,
        pwdResetRequired: false,
      }))
    })
    await page.unroute('**/admin-api/ims/auth/me')
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        id: '10',
        menus: [menu('/ims/workbench', '工作台')],
        permCodes: [],
      })))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_r10', 'Test1234')
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/ims/workbench')
    await expect(page.getByTestId('unassigned-panel')).toHaveCount(0)
    await expect(page.getByTestId('denied-panel')).toHaveCount(0)
    const sidebar = page.locator('.app-sidebar')
    await expect(sidebar).toHaveCount(1)
    const width = page.viewportSize()?.width ?? 1440
    if (width <= 390) {
      await page.locator('.app-layout').first().locator('> .app-main > .app-topbar .menu-btn').click()
    }
    await expect(sidebar.locator('.el-menu-item')).toHaveCount(1)
    await expect(sidebar.getByText('工作台')).toHaveCount(1)
    await expect(page.locator('.no-menu-tip')).toHaveCount(0)

    // 地址栏直接打开组织页、岗位页，都停在无权限页，不渲染业务表格。
    await page.goto('/ims/auth/org')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    await expect(page.locator('.el-table')).toHaveCount(0)
    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    await page.goto('/ims/auth/position')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    await expect(page.locator('.el-table')).toHaveCount(0)
    await expect(page).toHaveURL(/\/ims\/auth\/position/)
  })

  test('1215 锁定提示按用户名禁用登录，改用户名后恢复', async ({ page }) => {
    await installAuth(page, async (route) => {
      await fulfillLogin(route, fail(1215, '账号已锁定，请 15 分钟后再试', { remainMinutes: 15 }))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_lock', 'Wrong1234')
    const banner = page.getByTestId('login-banner')
    await expect(banner).toHaveText('账号已锁定，请 15 分钟后再试')
    await expect(page.getByRole('button', { name: '登录' })).toBeDisabled()
    await page.getByPlaceholder('请输入用户名').fill('test_yg')
    await expect(page.getByRole('button', { name: '登录' })).toBeEnabled()
    await page.getByPlaceholder('请输入用户名').fill('test_lock')
    await expect(page.getByRole('button', { name: '登录' })).toBeDisabled()
    await expect(page).toHaveURL(/\/login/)
  })

  test('1216 与 1008 使用固定提示且不进入系统', async ({ page }) => {
    let code = 1216
    await installAuth(page, async (route) => {
      const msg = code === 1216 ? '账号已冻结或已离职，无法登录' : '暂无权限'
      await fulfillLogin(route, fail(code, msg))
    })
    await page.goto('/login?redirect=/ims/workbench')
    await submitLogin(page, 'test_frozen', 'Test1234')
    await expect(page.getByTestId('login-banner')).toHaveText('账号已冻结或已离职，无法登录，请联系管理员')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.evaluate(() => localStorage.getItem('ims_access_token'))).resolves.toBeNull()

    code = 1008
    await submitLogin(page, 'test_t2', 'Test1234')
    await expect(page.getByTestId('login-banner')).toHaveText('所属组织已停用，请联系管理员')
    await expect(page).toHaveURL(/\/login/)
  })

  test('网络错误只提示一次且登录不自动重试，5007 提示系统繁忙', async ({ page }) => {
    let calls = 0
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      calls += 1
      await route.abort('failed')
    })
    await page.goto('/login')
    await submitLogin(page, 'test_admin', 'Test1234')
    await expect(page.locator('.el-message').filter({ hasText: '网络异常，请检查网络后重试' })).toBeVisible()
    expect(calls).toBe(1)

    await page.unroute('**/admin-api/ims/auth/login')
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await route.fulfill(json(fail(5007, '系统繁忙，请稍后再试')))
    })
    await submitLogin(page, 'test_admin', 'Test1234')
    const busy = page.locator('.el-message').filter({ hasText: '系统繁忙，请稍后再试' })
    await expect(busy).toBeVisible()
    await expect(busy).not.toContainText('问题编号')
  })

  test('E2E-B1-LG-10/11 改密校验、成功跳转与退出', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'reset-token',
        refreshToken: 'reset-refresh',
        expiresIn: 7200,
        pwdResetRequired: true,
      }))
    })
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({ menus: [menu('/demo/tokens', 'Token 演示')] })))
    })
    await page.route('**/admin-api/ims/auth/logout', async (route) => {
      await route.fulfill(json(ok(null)))
    })
    let changeCalls = 0
    await page.route('**/admin-api/ims/auth/password/change', async (route) => {
      changeCalls += 1
      const body = route.request().postDataJSON() as { oldPassword: string; newPassword: string }
      expect(body.oldPassword).toBe('Test1234')
      expect(body.newPassword).toBe('Abcd5678!')
      await route.fulfill(json(ok(null)))
    })

    await page.goto('/login')
    await submitLogin(page, 'test_reset', 'Test1234')
    await expect(page).toHaveURL(/\/password-reset/)
    await expect(page.getByRole('heading', { name: '请先修改密码' })).toBeVisible()
    await expect(page.locator('.app-sidebar')).toHaveCount(0)

    const width = page.viewportSize()?.width ?? 1440
    if (width <= 390) {
      await expectNoHOverflow(page, 390)
      const card = await page.getByTestId('password-card').boundingBox()
      expect(card!.width).toBeLessThanOrEqual(390)
      const logout = await page.getByRole('button', { name: '退出登录' }).boundingBox()
      expect(logout!.height).toBeGreaterThanOrEqual(44)
    }

    await page.goto('/demo/layout')
    await expect(page).toHaveURL(/\/password-reset/)

    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('请输入当前密码')).toBeVisible()
    await expect(page.getByText('请输入新密码')).toBeVisible()
    await expect(page.getByText('请输入确认新密码')).toBeVisible()
    expect(changeCalls).toBe(0)

    await page.getByPlaceholder('请输入当前密码').fill('Test1234')
    await page.getByPlaceholder('请输入新密码').fill('abcdefgh')
    await page.getByPlaceholder('请再次输入新密码').fill('abcdefgh')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('密码需 8～32 位，且同时包含字母和数字')).toBeVisible()

    await page.getByPlaceholder('请输入新密码').fill('Abcd 5678')
    await page.getByPlaceholder('请再次输入新密码').fill('Abcd 5678')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('密码不能包含空格')).toBeVisible()

    await page.getByPlaceholder('请输入新密码').fill('Abcd5678')
    await page.getByPlaceholder('请再次输入新密码').fill('Abcd5679')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('两次输入的新密码不一致')).toBeVisible()

    await page.getByPlaceholder('请输入新密码').fill('Test1234')
    await page.getByPlaceholder('请再次输入新密码').fill('Test1234')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('新密码不能与当前密码相同')).toBeVisible()
    expect(changeCalls).toBe(0)

    await page.getByPlaceholder('请输入新密码').fill('Abcd5678!')
    await page.getByPlaceholder('请再次输入新密码').fill('Abcd5678!')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.locator('.el-message').filter({ hasText: '密码已修改' })).toBeVisible()
    await expect(page).toHaveURL(/\/demo\/tokens/)
    expect(changeCalls).toBe(1)

    await page.evaluate(() => localStorage.clear())
    await page.goto('/login')
    await submitLogin(page, 'test_reset', 'Test1234')
    await expect(page).toHaveURL(/\/password-reset/)
    await page.getByRole('button', { name: '退出登录' }).click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.evaluate(() => localStorage.getItem('ims_access_token'))).resolves.toBeNull()
  })

  test('改密接口返回 1214 时停在改密页', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await fulfillLogin(route, ok({
        accessToken: 'reset-token',
        refreshToken: 'reset-refresh',
        expiresIn: 7200,
        pwdResetRequired: true,
      }))
    })
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload()))
    })
    await page.route('**/admin-api/ims/auth/password/change', async (route) => {
      await route.fulfill(json(fail(1214, '用户名或密码错误')))
    })
    await page.goto('/login')
    await submitLogin(page, 'test_reset', 'Test1234')
    await page.getByPlaceholder('请输入当前密码').fill('Wrong1234')
    await page.getByPlaceholder('请输入新密码').fill('Abcd5678')
    await page.getByPlaceholder('请再次输入新密码').fill('Abcd5678')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page.getByText('当前密码不正确')).toBeVisible()
    await expect(page).toHaveURL(/\/password-reset/)
  })

  test.skip('E2E-B1-LG-23 外协会话请求组织事件返回 1008（依赖组织同步后端 PR）', async ({ page }) => {
    // GET /admin-api/ims/auth/org/events 属于组织同步后端，main 上还没有这个接口。
    // test_r10 已在种子里。接口合入后再去掉 skip。用 page.request 带令牌，不依赖 Vite 源码模块。
    await page.goto('/login')
    await submitLogin(page, 'test_r10', 'Test1234')
    const token = await page.evaluate(() => localStorage.getItem('ims_access_token'))
    expect(token).toEqual(expect.any(String))
    expect(token).not.toBe('')
    const response = await page.request.get('/admin-api/ims/auth/org/events', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const body = (await response.json()) as { code?: number }
    expect(body.code).toBe(1008)
  })
})
