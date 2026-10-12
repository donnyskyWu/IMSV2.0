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
 * 4. 登录后 URL 离开 /login（不指定落地页）。侧栏里出现的名字必须来自 /me。
 *    现在的 main 会进示例页并画出这些名字；#12 只画已登记叶子，没登记时可以没有菜单项。
 * 5. 不带令牌 GET /admin-api/ims/auth/me，经 Vite 返回 HTTP 401 且 code 为 1002。
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
    const menuNames = collectMenuNames(me.body.data?.menus)
    expect(menuNames.length).toBeGreaterThan(0)

    // 不带 redirect。现在会进 /demo/tokens；#12 只落到已登记的菜单叶子，否则停在壳路径。
    await page.waitForURL((url) => url.pathname !== '/login')
    const sidebar = page.locator('[data-testid="app-sidebar"]')
    await expect(sidebar).toBeVisible()
    const sidebarEntries = sidebar.locator('.el-menu-item, .el-sub-menu__title')
    const sidebarText = (await sidebarEntries.allTextContents()).join('\n')
    const matched = menuNames.filter((name) => sidebarText.includes(name))
    // 画出的每一项都得是 /me 的名字。示例 mock（Token 演示等）不在种子菜单里，出现即失败。
    const shown = (await sidebarEntries.allTextContents()).map((text) => text.trim()).filter(Boolean)
    for (const text of shown) {
      expect(menuNames.some((name) => text.includes(name))).toBe(true)
    }
    // 当前 main 的示例页会把 /me 铺进侧栏，至少对上一个名字。
    // #12 在叶子都未登记时侧栏没有菜单项；上面的循环已经保证画出来的名字都属于 /me。
    if (new URL(page.url()).pathname.startsWith('/demo/')) {
      expect(matched.length).toBeGreaterThan(0)
    }
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
})
