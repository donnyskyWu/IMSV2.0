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
 * 4. 登录后进入带侧栏的页面，侧栏至少出现一个 /me 返回的菜单名
 */
import { expect, test } from '@playwright/test'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
const username = env?.E2E_SEED_USERNAME
const password = env?.E2E_SEED_PASSWORD
if (!username || !password) {
  throw new Error('缺少 E2E_SEED_USERNAME / E2E_SEED_PASSWORD，应由 tools.seed.users 注入')
}

interface MenuNode {
  name?: string
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

test.describe('Vite 代理联通真实后端', () => {
  test('health 为 UP，种子账号登录后 /me 有菜单且侧栏可见', async ({ page }) => {
    await page.goto('/login?redirect=/demo/layout')
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto('/login?redirect=/demo/layout')

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
    const menuNames = collectMenuNames(me.body.data?.menus)
    expect(menuNames.length).toBeGreaterThan(0)

    await page.waitForURL('**/demo/layout')
    const sidebarEntries = page.locator('[data-testid="app-sidebar"] .el-menu-item, [data-testid="app-sidebar"] .el-sub-menu__title')
    await expect(sidebarEntries.first()).toBeVisible()
    const sidebarText = (await sidebarEntries.allTextContents()).join('\n')
    expect(menuNames.some((name) => sidebarText.includes(name))).toBe(true)
  })
})
