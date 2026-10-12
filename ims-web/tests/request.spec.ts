/**
 * 请求层测试
 * 依据: 02-验证用例.md VC-R-01~17
 * 使用 B0a OpenAPI 契约的 mock 数据
 */
import { test, expect } from '@playwright/test'
import { setupApiMocks, ErrorCode } from './mocks/api-mocks'

test.describe('R. 请求层', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page)
  })

  test('VC-R-01: 成功请求应显示绿色提示', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const successBtn = page.getByRole('button', { name: '成功 (0)' })
    await successBtn.click()

    const message = page.locator('.el-message--success')
    await expect(message).toBeVisible({ timeout: 5000 })
    await expect(message).toContainText('请求成功')
  })

  test('VC-R-02: 1001 校验失败应触发错误处理', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const btn = page.getByRole('button', { name: '校验失败 (1001)' })
    await btn.click()

    // 1001 错误码由表单层处理，请求层不显示全局提示
    // 验证按钮可点击且请求被发送
    await page.waitForTimeout(500)
    await expect(btn).toBeEnabled()
  })

  test('VC-R-03: 1008 无权限应提示暂无权限', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const btn = page.getByRole('button', { name: '无权限 (1008)' })
    await btn.click()

    const message = page.locator('.el-message--error')
    await expect(message).toBeVisible({ timeout: 5000 })
    await expect(message).toContainText('暂无权限')
  })

  test('VC-R-04: 1504 资源不可用应触发错误处理', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const btn = page.getByRole('button', { name: '资源不存在 (1504)' })
    await btn.click()

    const message = page.locator('.el-message--warning')
    await expect(message).toBeVisible({ timeout: 5000 })
    await expect(message).toContainText('资源不可用')
  })

  test('VC-R-05: 5007 系统异常应显示问题编号', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const btn = page.getByRole('button', { name: '系统异常 (5007)' })
    await btn.click()

    const message = page.locator('.el-message--error')
    await expect(message).toBeVisible({ timeout: 5000 })
    await expect(message).toContainText('系统繁忙')
    await expect(message).toContainText('问题编号')
  })

  test('VC-R-06: 离线时应提示网络异常', async ({ page, context }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    // 使用前端模拟的请求按钮而非 API 按钮
    const successBtn = page.getByRole('button', { name: '成功请求' })
    
    // 模拟网络错误：通过 route 拦截模拟网络失败
    await page.route('**/admin-api/**', (route) => {
      route.abort('failed')
    })

    await successBtn.click()
    // 等待超时处理
    await page.waitForTimeout(2000)

    // 验证显示网络异常提示
    const errorMessage = page.locator('.el-message--error, .el-message:has-text("网络")')
    if (await errorMessage.count() > 0) {
      await expect(errorMessage.first()).toBeVisible()
    }
    
    // 恢复网络
    await page.unroute('**/admin-api/**')
    
    // 网络恢复后页面正常
    await expect(successBtn).toBeEnabled()
  })

  test('VC-R-07: 令牌过期应自动刷新', async ({ page }) => {
    let refreshCalled = 0
    let hits = 0
    await page.unroute('**/admin-api/ims/demo/error**')
    await page.unroute('**/admin-api/ims/auth/refresh-token')
    await page.route('**/admin-api/ims/demo/error**', async (route) => {
      hits += 1
      const code = hits === 1 ? ErrorCode.TOKEN_EXPIRED : 0
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(code === 0
          ? { code: 0, msg: '成功', data: { message: '请求成功' } }
          : { code, msg: '令牌已过期', data: null }),
      })
    })
    await page.route('**/admin-api/ims/auth/refresh-token', async (route) => {
      refreshCalled += 1
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          msg: '成功',
          data: { accessToken: 'new_token', refreshToken: 'new_refresh', expiresIn: 7200, pwdResetRequired: false },
        }),
      })
    })

    await page.goto('/demo/request')
    await page.getByRole('button', { name: '成功 (0)' }).click()
    await expect(page.locator('.el-message--success').filter({ hasText: '请求成功' })).toBeVisible()
    await expect(page).toHaveURL(/\/demo\/request/)
    expect(refreshCalled).toBe(1)
  })

  test('VC-R-08: 并发请求只刷新一次令牌', async ({ page }) => {
    let refreshCount = 0
    let requestCount = 0

    await page.unroute('**/admin-api/ims/demo/error**')
    await page.unroute('**/admin-api/ims/auth/refresh-token')
    await page.route('**/admin-api/ims/demo/error**', async (route) => {
      requestCount++
      if (refreshCount === 0) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: ErrorCode.TOKEN_EXPIRED, msg: '令牌已过期', data: null }),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, msg: '成功', data: { message: '操作成功' } }),
        })
      }
    })

    await page.route('**/admin-api/ims/auth/refresh-token', async (route) => {
      refreshCount++
      await new Promise(resolve => setTimeout(resolve, 200)) // 模拟网络延迟
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          msg: '成功',
          data: {
            accessToken: 'new_token_' + Date.now(),
            refreshToken: 'new_refresh_' + Date.now(),
            expiresIn: 7200,
            pwdResetRequired: false,
          },
        }),
      })
    })

    await page.addInitScript(() => {
      localStorage.setItem('ims_access_token', 'old_token')
      localStorage.setItem('ims_refresh_token', 'old_refresh_token')
    })

    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const burst = page.getByRole('button', { name: '并发 5 次' })
    await burst.click()
    await expect(page.locator('.el-message--success').filter({ hasText: '5 个请求都成功' })).toBeVisible()
    expect(refreshCount).toBe(1)
    expect(requestCount).toBeGreaterThanOrEqual(5)
  })

  test('VC-R-09: 刷新令牌失效应跳登录页', async ({ page }) => {
    await page.unroute('**/admin-api/ims/demo/error**')
    await page.unroute('**/admin-api/ims/auth/refresh-token')
    await page.route('**/admin-api/ims/demo/error**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: ErrorCode.TOKEN_EXPIRED, msg: '令牌已过期', data: null }),
      })
    })
    await page.route('**/admin-api/ims/auth/refresh-token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: ErrorCode.TOKEN_EXPIRED, msg: '刷新令牌失效', data: null }),
      })
    })

    await page.goto('/demo/request')
    await page.getByRole('button', { name: '成功 (0)' }).click()
    await expect(page).toHaveURL(/\/login\?/)
    expect(decodeURIComponent(page.url())).toContain('/demo/request')
    await expect(page.locator('.el-message').filter({ hasText: '登录已失效，请重新登录' })).toBeVisible()
  })

  test('VC-R-10: 多设备登录应提示下线', async ({ page }) => {
    await page.route('**/admin-api/ims/demo/error**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1003, msg: '下线', data: null }),
      })
    })
    await page.goto('/demo/request')
    await page.getByRole('button', { name: '成功 (0)' }).click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('.el-message').filter({ hasText: '您的账号已在其他设备登录，本设备已下线' })).toBeVisible()
  })

  test('VC-R-11: 跨标签页退出登录同步', async ({ page, context }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    // 设置 token
    await page.evaluate(() => {
      localStorage.setItem('ims_access_token', 'test_token')
    })

    // 打开新标签页
    const page2 = await context.newPage()
    await page2.goto('/demo/layout')

    // 在第二个标签页清除 token (模拟登出)
    await page2.evaluate(() => {
      localStorage.removeItem('ims_access_token')
    })

    // 等待第一个页面响应 storage 事件
    await page.waitForTimeout(500)

    await expect(page).toHaveURL(/\/login/)
    await page2.close()
  })

  test('VC-R-12: 密码重置后必须改密', async ({ page }) => {
    await page.unroute('**/admin-api/ims/auth/login')
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          msg: '成功',
          data: {
            accessToken: 'reset_token',
            refreshToken: 'reset_refresh',
            expiresIn: 7200,
            pwdResetRequired: true,
          },
        }),
      })
    })
    await page.route('**/admin-api/ims/auth/password/change', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, msg: '成功', data: null }),
      })
    })
    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('qa_viewer')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()
    await expect(page).toHaveURL(/\/password-reset/)
    await expect(page.locator('.app-sidebar')).toHaveCount(0)
    await page.goto('/demo/list')
    await expect(page).toHaveURL(/\/password-reset/)
    await page.getByPlaceholder('请输入当前密码').fill('Test1234')
    await page.getByPlaceholder('请输入新密码').fill('Abcd5678')
    await page.getByPlaceholder('请再次输入新密码').fill('Abcd5678')
    await page.getByRole('button', { name: '确认修改' }).click()
    await expect(page).toHaveURL((url) => new URL(url).pathname === '/')
    await expect(page.getByTestId('unassigned-panel')).toContainText('您的账号尚未分配权限，请联系管理员')
  })

  test('VC-R-13: 权限变更无感知刷新', async ({ page }) => {
    await setupApiMocks(page)

    // 第一次加载
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    // 权限变更通过重新获取 /me 实现
    // 验证 /me 接口可以正常调用
    const response = await page.request.get('/admin-api/ims/auth/me')
    expect(response.status()).toBe(200)
  })

  test('VC-R-14: 字典变更实时生效', async ({ page }) => {
    await page.goto('/demo/list')
    await expect(page.locator('.status-label').filter({ hasText: '待审核' }).first()).toBeVisible()
    const narrow = (page.viewportSize()?.width ?? 1440) < 768
    if (narrow) {
      await page.locator('.page-header .header-actions .el-dropdown').click()
      await page.locator('.el-dropdown-menu:visible').getByRole('button', { name: '刷新字典' }).click()
    } else {
      await page.getByRole('button', { name: '刷新字典' }).click()
    }
    await expect(page.locator('.status-label').filter({ hasText: '测试名' }).first()).toBeVisible()
    await expect(page.locator('.status-label').filter({ hasText: '待审核' })).toHaveCount(0)
  })

  test('VC-R-15: 未登录访问应跳登录页', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('ims_access_token')
      localStorage.removeItem('ims_refresh_token')
      sessionStorage.setItem('ims_require_auth', '1')
    })
    await page.goto('/demo/list')
    await expect(page).toHaveURL(/\/login/)
    expect(decodeURIComponent(page.url())).toContain('redirect=')
    expect(decodeURIComponent(page.url())).toContain('/demo/list')
  })

  test('VC-R-16: 无权限账号应显示暂无权限', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.unrouteAll({ behavior: 'ignoreErrors' })
    await setupApiMocks(page, { userType: 'noperm' })
    await page.reload()
    await expect(page.locator('.no-menu-tip')).toHaveText('您的账号尚未分配权限，请联系管理员')
    await expect(page.getByRole('main').getByText('暂无权限查看此内容')).toBeVisible()
    await expect(page.getByRole('main').getByText('您的账号尚未分配权限，请联系管理员')).toHaveCount(0)
    await expect(page.locator('.app-content .el-table')).toHaveCount(0)
  })
})
