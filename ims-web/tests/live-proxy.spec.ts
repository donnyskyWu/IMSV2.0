/**
 * 开发代理联通（fix B0b）。
 * 浏览器只访问 Vite（127.0.0.1:3000），由代理转到真实后端。
 * 禁止 page.route / 网络 mock。
 * 账号由 playwright.live.config.ts 从 tools.seed.users 注入，不在这里写死。
 *
 * 断言：
 * 1. GET /health 的 data.db 为 UP
 * 2. 种子账号经登录页真实登录并拿到访问令牌
 * 3. 带该令牌 GET /admin-api/ims/auth/me，code=0 且菜单非空
 * 4. 登录后 URL 离开 /login。侧栏画出已登记叶子：顶层能看到「权限管理」，
 *    至少一项可点，点击后地址变为该项在 /me 里的 path。
 * 5. test_r10 只授工作台：侧栏没有可点项，内容区显示未分配权限。
 * 6. 不带令牌 GET /admin-api/ims/auth/me，经 Vite 返回 HTTP 401 且 code 为 1002。
 * 7. 登录后把 access token 换成用 IMS_JWT_SECRET 签的过期令牌，刷新令牌仍是登录拿到的。
 *    打开页面后经 Vite 调 /me：刷新接口只出现 1 次，最终 /me 为 200，地址不回登录页。
 */
import { createHmac } from 'node:crypto'

import { expect, test } from '@playwright/test'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
const username = env?.E2E_SEED_USERNAME
const password = env?.E2E_SEED_PASSWORD
if (!username || !password) {
  throw new Error('缺少 E2E_SEED_USERNAME / E2E_SEED_PASSWORD，应由 tools.seed.users 注入')
}

interface MenuNode {
  name?: string
  path?: string
  children?: MenuNode[]
}

function collectMenuNames(menus: MenuNode[] | undefined): string[] {
  const names: string[] = []
  for (const item of menus || []) {
    if (item.name) names.push(item.name)
    names.push(...collectMenuNames(item.children))
  }
  return names
}

function collectLeafPaths(menus: MenuNode[] | undefined): Array<{ name: string; path: string }> {
  const leaves: Array<{ name: string; path: string }> = []
  for (const item of menus || []) {
    if (item.children && item.children.length > 0) {
      leaves.push(...collectLeafPaths(item.children))
      continue
    }
    if (item.name && item.path?.startsWith('/')) {
      leaves.push({ name: item.name, path: item.path.split('?')[0] || item.path })
    }
  }
  return leaves
}

test.describe('Vite 代理联通真实后端', () => {
  test('health 为 UP，种子账号登录后 /me 有菜单且侧栏可见', async ({ page }) => {
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto('/login')

    const health = await page.evaluate(async () => {
      const response = await fetch('/health')
      const body = await response.json()
      return { status: response.status, url: response.url, body }
    })
    expect(new URL(health.url).origin).toBe('http://127.0.0.1:3000')
    expect(health.status).toBe(200)
    expect(health.body.code).toBe(0)
    expect(health.body.data.db).toBe('UP')

    await page.getByPlaceholder('用户名').fill(username)
    await page.getByPlaceholder('密码').fill(password)
    const loginResponsePromise = page.waitForResponse(
      (response) => response.url().includes('/admin-api/ims/auth/login') && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '登录' }).click()
    const loginResponse = await loginResponsePromise
    expect(new URL(loginResponse.url()).origin).toBe('http://127.0.0.1:3000')
    const loginBody = await loginResponse.json()
    expect(loginBody.code).toBe(0)
    const accessToken = loginBody.data?.accessToken as string | undefined
    expect(accessToken).toBeTruthy()
    if (!accessToken || accessToken.startsWith('mock-')) {
      throw new Error('登录没有返回真实访问令牌')
    }

    await expect.poll(async () => page.evaluate(() => localStorage.getItem('ims_access_token'))).toBe(accessToken)

    const me = await page.evaluate(async (token) => {
      const response = await fetch('/admin-api/ims/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const body = await response.json()
      return { status: response.status, url: response.url, body }
    }, accessToken)
    expect(new URL(me.url).origin).toBe('http://127.0.0.1:3000')
    expect(me.url).toContain('/admin-api/ims/auth/me')
    expect(me.status).toBe(200)
    expect(me.body.code).toBe(0)
    const menus = me.body.data?.menus as MenuNode[] | undefined
    const menuNames = collectMenuNames(menus)
    expect(menuNames.length).toBeGreaterThan(0)
    expect((menus || []).map((item) => item.name)).toContain('权限管理')

    await page.waitForURL((url) => url.pathname !== '/login')
    const sidebar = page.locator('[data-testid="app-sidebar"]')
    await expect(sidebar).toBeVisible()
    await expect(sidebar.getByText('权限管理')).toBeVisible()
    await expect(sidebar.getByText('系统管理')).toHaveCount(0)
    const clickable = sidebar.locator('.el-menu-item')
    expect(await clickable.count(), '侧栏至少要有一项已登记且带 path 的可点叶子').toBeGreaterThan(0)
    const label = '岗位-角色供给规则'
    const target = collectLeafPaths(menus).find((item) => item.name === label)
    expect(target?.path, `可点项「${label}」必须对应 /me 里带 path 的叶子`).toBe('/ims/auth/position')
    const item = sidebar.getByRole('menuitem', { name: label })
    await expect(item).toBeVisible()
    await item.click()
    await expect(page).toHaveURL((url) => url.pathname === target?.path)
    await expect(page.getByTestId('b1-page-title')).toHaveText(label)
  })

  test('E2E-B1-LG-23 test_r10 只授工作台时侧栏为空并显示未分配权限', async ({ page }) => {
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto('/login')
    await page.getByPlaceholder('用户名').fill('test_r10')
    await page.getByPlaceholder('密码').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await expect(page).toHaveURL((url) => url.pathname === '/')
    await expect(page.getByTestId('unassigned-panel')).toHaveText('您的账号尚未分配权限，请联系管理员')
    await expect(page.locator('.app-sidebar .el-menu-item')).toHaveCount(0)
    await expect(page.locator('.app-sidebar').getByText('工作台')).toHaveCount(0)
    await expect(page.locator('.no-menu-tip')).toHaveCount(0)

    await page.goto('/ims/auth/org')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    await expect(page.locator('.el-table')).toHaveCount(0)
    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    await page.goto('/ims/auth/position')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
    await expect(page.locator('.el-table')).toHaveCount(0)
    await expect(page).toHaveURL(/\/ims\/auth\/position/)
  })

  test('不带令牌经 Vite 调用 /me 返回 401 与 1002', async ({ page }) => {
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    const me = await page.evaluate(async () => {
      const response = await fetch('/admin-api/ims/auth/me')
      const body = await response.json()
      return { status: response.status, url: response.url, body }
    })
    expect(new URL(me.url).origin).toBe('http://127.0.0.1:3000')
    expect(me.url).toContain('/admin-api/ims/auth/me')
    expect(me.status).toBe(401)
    expect(me.body.code).toBe(1002)
  })

  test('过期访问令牌经 Vite 静默刷新后 /me 为 200 且不回登录页', async ({ page }) => {
    const secret = env?.IMS_JWT_SECRET
    if (!secret) {
      throw new Error('缺少 IMS_JWT_SECRET，无法用与后端相同的密钥签发过期访问令牌')
    }

    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto('/login')
    await page.getByPlaceholder('用户名').fill(username)
    await page.getByPlaceholder('密码').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL((url) => url.pathname !== '/login')

    const stored = await page.evaluate(() => ({
      accessToken: localStorage.getItem('ims_access_token'),
      refreshToken: localStorage.getItem('ims_refresh_token'),
    }))
    if (!stored.accessToken || !stored.refreshToken) {
      throw new Error('登录没有写入访问令牌或刷新令牌')
    }
    const expiredAccess = signExpiredAccessToken(stored.accessToken, secret)
    expect(expiredAccess).not.toBe(stored.accessToken)

    let refreshCount = 0
    page.on('request', (request) => {
      if (request.url().includes('/admin-api/ims/auth/refresh-token') && request.method() === 'POST') {
        refreshCount += 1
      }
    })
    const refreshResponse = page.waitForResponse(
      (response) => response.url().includes('/admin-api/ims/auth/refresh-token') && response.request().method() === 'POST',
    )
    const meOk = page.waitForResponse(
      (response) => response.url().includes('/admin-api/ims/auth/me') && response.request().method() === 'GET' && response.status() === 200,
    )

    await page.evaluate((token) => {
      localStorage.setItem('ims_access_token', token)
    }, expiredAccess)
    await page.reload()

    const refreshed = await refreshResponse
    expect(new URL(refreshed.url()).origin).toBe('http://127.0.0.1:3000')
    const refreshBody = await refreshed.json()
    expect(refreshBody.code).toBe(0)
    expect(refreshBody.data?.accessToken).toBeTruthy()

    const me = await meOk
    expect(new URL(me.url()).origin).toBe('http://127.0.0.1:3000')
    const meBody = await me.json()
    expect(me.status()).toBe(200)
    expect(meBody.code).toBe(0)
    expect(refreshCount).toBe(1)
    await expect(page).not.toHaveURL(/\/login/)
    await expect.poll(async () => page.evaluate(() => localStorage.getItem('ims_access_token'))).not.toBe(expiredAccess)
  })
})

function signExpiredAccessToken(accessToken: string, secret: string): string {
  const payloadPart = accessToken.split('.')[1]
  if (!payloadPart) {
    throw new Error('登录返回的访问令牌不是 JWT，无法改签过期时间')
  }
  const claims = JSON.parse(Buffer.from(payloadPart, 'base64url').toString('utf8')) as Record<string, unknown>
  const now = Math.floor(Date.now() / 1000)
  const header = base64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = base64Url(JSON.stringify({
    sub: claims.sub,
    tid: claims.tid,
    sid: claims.sid,
    iat: now - 7200,
    exp: now - 60,
    type: 'access',
  }))
  const unsigned = `${header}.${payload}`
  const signature = createHmac('sha256', secret).update(unsigned).digest('base64url')
  return `${unsigned}.${signature}`
}

function base64Url(value: string): string {
  return Buffer.from(value).toString('base64url')
}
