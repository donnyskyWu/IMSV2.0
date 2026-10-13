/**
 * 生产构建冒烟。只在 prod-build（vite preview）里真跑。
 * 无菜单账号的 mock 与 auth-login.spec.ts 的 E2E-B1-LG-09 一致。
 * 不用 test_admin：#15 合入后超管有菜单，会落到第一个菜单页。
 */
import { test, expect, type Page, type Route } from '@playwright/test'

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

async function installNoMenuAuth(page: Page) {
  await page.route('**/admin-api/ims/auth/login', async (route: Route) => {
    await route.fulfill(json(ok({
      accessToken: 'access-norole',
      refreshToken: 'refresh-norole',
      expiresIn: 7200,
      pwdResetRequired: false,
    })))
  })
  await page.route('**/admin-api/ims/auth/me', async (route: Route) => {
    const authorization = route.request().headers().authorization || ''
    const token = authorization.toLowerCase().startsWith('bearer ')
      ? authorization.slice(7).trim()
      : ''
    // 未登录与后端 #17 一致：HTTP 401 + code 1002。
    if (!token) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1002, msg: '登录已失效，请重新登录', data: null }),
      })
      return
    }
    await route.fulfill(json(ok({
      user: {
        id: '9',
        username: 'test_norole',
        nickname: '无角色',
        avatar: null,
        deptNames: ['信息部'],
        mainDeptName: '信息部',
        positionLabel: null,
        pwdResetRequired: false,
      },
      menus: [],
      permCodes: [],
      permDetails: {},
      dataScopeText: '暂无权限',
    })))
  })
  await page.route('**/admin-api/ims/auth/logout', async (route: Route) => {
    await route.fulfill(json(ok(null)))
  })
}

test('B1-PROD-01 生产构建无菜单账号落到未分配权限提示', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'prod-build', '仅在 prod-build 项目中运行')

  await installNoMenuAuth(page)
  await page.goto('/login')
  await page.getByPlaceholder('请输入用户名').fill('test_norole')
  await page.getByPlaceholder('请输入密码').fill('Test1234')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page).toHaveURL((url) => new URL(url).pathname === '/')
  await expect(page.getByTestId('unassigned-panel')).toHaveText('您的账号尚未分配权限，请联系管理员')
  await expect(page.locator('.app-sidebar')).toHaveCount(1)
  await expect(page.locator('.app-sidebar .el-menu-item')).toHaveCount(0)
})
