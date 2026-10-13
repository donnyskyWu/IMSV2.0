/**
 * 个人中心 E2E-B2-PC-01～03。
 * 只在 playwright.live.config.ts 的 desktop-chromium 跑：浏览器走 Vite，接口打真实后端。
 * 断言页面结构（PageHeader / Tabs / DescriptionList / DataTable / FormField）和响应式，不只对文案。
 * PC-02 的钉钉登录用 mock 模式，不扫码。
 */
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test, type Page } from '@playwright/test'

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
const password = env?.E2E_SEED_PASSWORD
if (!password) {
  throw new Error('缺少 E2E_SEED_PASSWORD，应由 tools.seed.users 注入')
}

const DING_USERNAME = 'mock_dingtalk_user_001'
const SET_PASSWORD = 'Ding5678!'

function clearDingPassword() {
  const backendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../ims-backend')
  const python = env?.PYTHON || 'python3'
  execFileSync(python, ['-c', `
import os
os.environ.setdefault("IMS_ENV", "dev")
from app.db.session import init_db, use_db_session
from app.domains.sys.models import User
init_db()
with use_db_session() as session:
    user = session.query(User).filter(User.username == "${DING_USERNAME}", User.deleted == 0).one()
    user.password_hash = ""
    session.commit()
`], {
    cwd: backendRoot,
    env: { ...process.env, PYTHONPATH: backendRoot },
  })
}

async function resetBrowser(page: Page) {
  await page.goto('/login')
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await page.goto('/login')
}

async function login(page: Page, username: string, userPassword: string) {
  await resetBrowser(page)
  await page.getByPlaceholder('用户名').fill(username)
  await page.getByPlaceholder('密码').fill(userPassword)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).not.toHaveURL(/\/login/)
}

async function openProfile(page: Page) {
  await page.locator('.app-layout .user-dropdown').click()
  await page.locator('.el-dropdown-menu:visible').getByRole('menuitem', { name: '个人中心' }).click()
  await expect(page).toHaveURL(/\/profile/)
  await expect(page.getByTestId('profile-page')).toBeVisible()
}

const INFO_LABELS = ['姓名', '用户名', '手机', '主部门', '所属部门', '岗位', '角色', '数据范围']

async function assertDesktopChrome(page: Page, passwordTab: string) {
  const root = page.getByTestId('profile-page')
  const title = root.locator('.page-title')
  await expect(title).toHaveText('个人中心')
  await expect(title).toHaveCSS('font-size', '28px')
  await expect(root.locator('.data-scope')).toHaveCount(0)
  const tabs = root.locator('.tab-item')
  await expect(tabs).toHaveCount(3)
  await expect(tabs.nth(0)).toHaveText('基本信息')
  await expect(tabs.nth(1)).toHaveText(passwordTab)
  await expect(tabs.nth(2)).toHaveText('我的会话')
}

async function assertInfoStructure(page: Page) {
  const info = page.getByTestId('profile-info')
  const list = info.locator('.description-list')
  await expect(list).toBeVisible()
  await expect(list).not.toHaveClass(/description-list--mobile/)
  await expect(info.locator('.desc-item')).toHaveCount(INFO_LABELS.length)
  for (const label of INFO_LABELS) {
    await expect(info.locator('.desc-label', { hasText: label })).toHaveCount(1)
  }
  const masked = info.locator('.desc-item', { hasText: '手机' }).locator('.masked-text')
  await expect(masked).toHaveCount(1)
  const mobile = (await masked.innerText()).trim()
  expect(mobile).not.toMatch(/^\d{11}$/)
  if (mobile) expect(mobile).toMatch(/\*/)
  await expect(info.locator('input, textarea, select')).toHaveCount(0)
}

async function assertMobileThenRestore(page: Page) {
  await page.setViewportSize({ width: 390, height: 844 })
  const root = page.getByTestId('profile-page')
  await expect(root.locator('.page-title')).toHaveCSS('font-size', '20px')
  await expect(root.locator('.description-list')).toHaveClass(/description-list--mobile/)
  await expect(root.locator('.desc-item')).toHaveCount(INFO_LABELS.length)
  await page.setViewportSize({ width: 1440, height: 900 })
  await expect(root.locator('.page-title')).toHaveCSS('font-size', '28px')
  await expect(root.locator('.description-list')).not.toHaveClass(/description-list--mobile/)
}

async function openTab(page: Page, label: string) {
  await page.getByTestId('profile-page').locator('.tab-item', { hasText: label }).click()
}

test('E2E-B2-PC-01 查看资料并修改密码', async ({ page }) => {
  await login(page, 'test_yg', password)
  await openProfile(page)
  await assertDesktopChrome(page, '修改密码')
  await assertInfoStructure(page)
  await assertMobileThenRestore(page)

  await openTab(page, '修改密码')
  const form = page.getByTestId('password-change-form')
  await expect(form).toBeVisible()
  await expect(form.locator('.form-field')).toHaveCount(3)
  await expect(form.locator('.form-field').nth(0)).toContainText('当前密码')
  await expect(form.locator('.form-field').nth(1)).toContainText('新密码')
  await expect(form.locator('.form-field').nth(2)).toContainText('确认新密码')
  await expect(page.getByPlaceholder('请输入当前密码')).toBeVisible()
  await expect(page.getByPlaceholder('请输入新密码')).toBeVisible()
  await expect(page.getByPlaceholder('请再次输入新密码')).toBeVisible()

  await page.getByPlaceholder('请输入当前密码').fill('Wrong1234')
  await page.getByPlaceholder('请输入新密码').fill('Test5678')
  await page.getByPlaceholder('请再次输入新密码').fill('Test5678')
  const wrong = page.waitForResponse((response) => response.url().includes('/password/change'))
  await page.getByRole('button', { name: '确认修改' }).click()
  expect((await (await wrong).json()).code).toBe(1214)
  await expect(page.getByText('当前密码不正确')).toBeVisible()

  await page.getByPlaceholder('请输入当前密码').fill(password)
  const changed = page.waitForResponse((response) => response.url().includes('/password/change'))
  await page.getByRole('button', { name: '确认修改' }).click()
  expect((await (await changed).json()).code).toBe(0)
  await expect(page.getByText('密码已修改')).toBeVisible()
  const token = await page.evaluate(() => localStorage.getItem('ims_access_token'))
  const me = await page.evaluate(async (access) => {
    const response = await fetch('/admin-api/ims/auth/me', {
      headers: { Authorization: `Bearer ${access}` },
    })
    return response.status
  }, token)
  expect(me).toBe(200)

  await page.getByPlaceholder('请输入当前密码').fill('Test5678')
  await page.getByPlaceholder('请输入新密码').fill(password)
  await page.getByPlaceholder('请再次输入新密码').fill(password)
  const restored = page.waitForResponse((response) => response.url().includes('/password/change'))
  await page.getByRole('button', { name: '确认修改' }).click()
  expect((await (await restored).json()).code).toBe(0)
})

test('E2E-B2-PC-02 钉钉用户设置密码', async ({ page }) => {
  clearDingPassword()
  const params = await page.request.get('/admin-api/ims/auth/sso/dingtalk/authorize-params?redirect=/profile')
  expect(params.ok()).toBeTruthy()
  const body = await params.json()
  expect(body.code).toBe(0)
  const state = body.data.state as string
  expect(state).toBeTruthy()

  await page.goto(`/admin-api/ims/auth/sso/dingtalk/callback?authCode=e2e-pc02&state=${encodeURIComponent(state)}`)
  await expect(page).toHaveURL(/\/profile/)
  await assertDesktopChrome(page, '设置密码')
  await expect(page.getByPlaceholder('请输入当前密码')).toHaveCount(0)

  await openTab(page, '设置密码')
  const setForm = page.getByTestId('password-set-form')
  await expect(setForm.locator('.form-field')).toHaveCount(2)
  await expect(setForm.getByText('当前密码', { exact: true })).toHaveCount(0)
  await page.getByPlaceholder('请输入新密码').fill(SET_PASSWORD)
  await page.getByPlaceholder('请再次输入新密码').fill(SET_PASSWORD)
  const tokenBefore = await page.evaluate(() => localStorage.getItem('ims_access_token'))
  const set = page.waitForResponse((response) => response.url().includes('/password/set'))
  await page.getByRole('button', { name: '设置密码' }).click()
  expect((await (await set).json()).code).toBe(0)
  await expect(page.getByText('密码已设置')).toBeVisible()
  const me = await page.evaluate(async (access) => {
    const response = await fetch('/admin-api/ims/auth/me', {
      headers: { Authorization: `Bearer ${access}` },
    })
    return response.status
  }, tokenBefore)
  expect(me).toBe(200)

  await login(page, DING_USERNAME, SET_PASSWORD)
  await expect(page.getByTestId('profile-page').or(page.locator('.app-layout'))).toBeVisible()
})

test('E2E-B2-PC-03 下线另一会话', async ({ page, browser }) => {
  await login(page, 'test_yg', password)
  await page.evaluate(async () => {
    const token = localStorage.getItem('ims_access_token') || ''
    const listed = await fetch('/admin-api/ims/auth/session/my', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const body = await listed.json()
    for (const row of body.data?.list || []) {
      if (row.current) continue
      await fetch(`/admin-api/ims/auth/session/my?sid=${encodeURIComponent(row.sid)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
    }
  })
  const other = await browser.newContext()
  const page2 = await other.newPage()
  await login(page2, 'test_yg', password)

  await openProfile(page)
  await assertDesktopChrome(page, '修改密码')
  await openTab(page, '我的会话')
  const sessions = page.getByTestId('session-list')
  const table = sessions.locator('.data-table-wrap')
  await expect(table).toBeVisible()
  await expect(table).not.toHaveClass(/data-table--mobile/)
  for (const header of ['设备', 'IP', '登录时间', '最后活跃', '当前', '操作']) {
    await expect(table.locator('th', { hasText: header })).toHaveCount(1)
  }
  await expect(sessions.locator('.el-table__body').getByText('当前', { exact: true })).toHaveCount(1)
  await expect(sessions.getByRole('button', { name: '下线' })).toHaveCount(1)
  await sessions.getByRole('button', { name: '下线' }).click()

  await page2.reload()
  await expect(page2).toHaveURL(/\/login/)
  await other.close()
})
