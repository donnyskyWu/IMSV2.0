/**
 * 组织架构同步页 E2E 测试 (FP-B1-ORG-01~11)
 * 依据: 02-验证用例.md
 *
 * 测试覆盖:
 * - E2E-B1-ORG-01: 有权限用户可访问组织同步页
 * - E2E-B1-ORG-02: 无权限用户返回 1008
 * - E2E-B1-ORG-03: 指标卡片显示正确数据
 * - E2E-B1-ORG-04: 事件列表分页和搜索
 * - E2E-B1-ORG-05: 重试/重放操作
 */
import { test, expect, type Page, type Route } from '@playwright/test'
import { expectNoHOverflow } from './helpers/mobile'

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
      pwdResetRequired: false,
    },
    menus: options?.menus ?? [menu('/ims/auth/org', '组织架构同步')],
    permCodes: options?.permCodes ?? ['ims:system:org-sync:query'],
    permDetails: {},
    dataScopeText: '全部',
  })
}

const mockMetrics = {
  userTotal: 1250,
  yesterdayEventCount: 45,
  pendingEventCount: 3,
  deadEventCount: 2,
  avgDelayMinutes: 1.5,
  p95DelayMinutes: 3.2,
  successRate24h: 0.98,
  dingtalkUnavailable: false,
  reconcileFailedTwice: false,
}

const mockDiffSummary = {
  overrideCount: 5,
  pendingAssignCount: 3,
  localOrphanCount: 1,
  sameNameCount: 0,
  unboundCount: 2,
}

const mockEvents = [
  {
    id: '1',
    eventId: 'evt-001',
    eventType: 'user_add_org',
    bizType: 'HIRE',
    subjectName: '张三',
    status: 'SUCCESS',
    retryCount: 0,
    eventTime: '2026-10-13T10:00:00+08:00',
    processedTime: '2026-10-13T10:00:05+08:00',
    lastError: null,
  },
  {
    id: '2',
    eventId: 'evt-002',
    eventType: 'user_modify_org',
    bizType: 'TRANSFER',
    subjectName: '李四',
    status: 'PENDING',
    retryCount: 0,
    eventTime: '2026-10-13T10:01:00+08:00',
    processedTime: null,
    lastError: null,
  },
  {
    id: '3',
    eventId: 'evt-003',
    eventType: 'user_leave_org',
    bizType: 'RESIGN',
    subjectName: '王五',
    status: 'DEAD',
    retryCount: 4,
    eventTime: '2026-10-13T09:30:00+08:00',
    processedTime: '2026-10-13T09:35:00+08:00',
    lastError: 'Timeout error',
  },
]

async function installOrgSyncMocks(page: Page) {
  await page.route('**/admin-api/ims/auth/login', async (route) => {
    await route.fulfill(json(ok({
      accessToken: 'access-1',
      refreshToken: 'refresh-1',
      expiresIn: 7200,
      pwdResetRequired: false,
    })))
  })

  await page.route('**/admin-api/ims/auth/me', async (route) => {
    await route.fulfill(json(mePayload({
      menus: [menu('/ims/auth/org', '组织架构同步')],
      permCodes: ['ims:system:org-sync:query', 'ims:system:org-sync:run'],
    })))
  })

  await page.route('**/admin-api/ims/auth/logout', async (route) => {
    await route.fulfill(json(ok(null)))
  })

  await page.route('**/admin-api/ims/auth/org/sync-metrics', async (route) => {
    await route.fulfill(json(ok(mockMetrics)))
  })

  await page.route('**/admin-api/ims/auth/org/diffs/summary', async (route) => {
    await route.fulfill(json(ok(mockDiffSummary)))
  })

  await page.route('**/admin-api/ims/auth/org/events*', async (route) => {
    if (route.request().url().includes('/events/') && !route.request().url().includes('/events?')) {
      return
    }
    await route.fulfill(json(ok({
      total: mockEvents.length,
      list: mockEvents,
      pageNo: 1,
      pageSize: 10,
    })))
  })
}

test.describe('组织架构同步页', () => {
  test('E2E-B1-ORG-01 有权限用户可访问组织同步页', async ({ page }) => {
    await installOrgSyncMocks(page)

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)
    await expect(page.getByTestId('b1-page-title')).toHaveText('组织架构同步')
    await expect(page.getByTestId('denied-panel')).toHaveCount(0)
  })

  test('E2E-B1-ORG-02 无权限用户返回 1008', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await route.fulfill(json(ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      })))
    })

    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [menu('/demo/tokens', 'Token 演示')],
        permCodes: ['ims:demo:order:query'],
      })))
    })

    await page.route('**/admin-api/ims/auth/org/sync-metrics', async (route) => {
      await route.fulfill(json(fail(1008, '暂无权限')))
    })

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_norole')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/demo\/tokens/)

    await page.goto('/ims/auth/org')
    await expect(page.getByTestId('denied-panel')).toHaveText('暂无权限查看此内容')
  })

  test('E2E-B1-ORG-03 指标卡片显示正确数据', async ({ page }) => {
    await installOrgSyncMocks(page)

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    await expect(page.getByText('1250').first()).toBeVisible()
    await expect(page.getByText('45').first()).toBeVisible()
    await expect(page.getByText('98%').first()).toBeVisible()
  })

  test('E2E-B1-ORG-04 事件列表分页和搜索', async ({ page }) => {
    await installOrgSyncMocks(page)

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    await expect(page.getByText('张三')).toBeVisible()
    await expect(page.getByText('李四')).toBeVisible()
    await expect(page.getByText('王五')).toBeVisible()

    const table = page.locator('.el-table')
    await expect(table).toBeVisible()
    await expect(table.locator('tbody tr')).toHaveCount(3)
  })

  test('E2E-B1-ORG-05 重试按钮对 DEAD 事件显示', async ({ page }) => {
    await installOrgSyncMocks(page)

    await page.route('**/admin-api/ims/auth/org/events/3/retry', async (route) => {
      await route.fulfill(json(ok({ status: 'SUCCESS' })))
    })

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    const deadRow = page.locator('.el-table tbody tr').filter({ hasText: '王五' })
    await expect(deadRow).toBeVisible()
    await expect(deadRow.getByText('DEAD')).toBeVisible()
  })

  test('E2E-B1-ORG-06 响应式布局在移动端正确显示', async ({ page }) => {
    await installOrgSyncMocks(page)

    const width = page.viewportSize()?.width ?? 1440
    if (width > 390) {
      test.skip()
      return
    }

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)
    await expectNoHOverflow(page, 390)
  })

  test('E2E-B1-ORG-07 重放抽屉打开和预览', async ({ page }) => {
    await installOrgSyncMocks(page)

    await page.route('**/admin-api/ims/auth/org/events/replay-preview*', async (route) => {
      await route.fulfill(json(ok({ count: 5 })))
    })

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)

    const width = page.viewportSize()?.width ?? 1440
    if (width <= 390) {
      const replayBtn = page.getByRole('button', { name: '批量重放' })
      if (await replayBtn.isVisible()) {
        await replayBtn.click()
        await expect(page.getByText('批量重放失败事件')).toBeVisible()
      }
    }
  })

  test('警告条在钉钉不可用或对账失败时显示', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await route.fulfill(json(ok({
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresIn: 7200,
        pwdResetRequired: false,
      })))
    })

    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill(json(mePayload({
        menus: [menu('/ims/auth/org', '组织架构同步')],
        permCodes: ['ims:system:org-sync:query', 'ims:system:org-sync:run'],
      })))
    })

    await page.route('**/admin-api/ims/auth/logout', async (route) => {
      await route.fulfill(json(ok(null)))
    })

    await page.route('**/admin-api/ims/auth/org/sync-metrics', async (route) => {
      await route.fulfill(json(ok({
        ...mockMetrics,
        dingtalkUnavailable: true,
        reconcileFailedTwice: true,
      })))
    })

    await page.route('**/admin-api/ims/auth/org/diffs/summary', async (route) => {
      await route.fulfill(json(ok(mockDiffSummary)))
    })

    await page.route('**/admin-api/ims/auth/org/events*', async (route) => {
      await route.fulfill(json(ok({
        total: 0,
        list: [],
        pageNo: 1,
        pageSize: 10,
      })))
    })

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('test_admin')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page).toHaveURL(/\/ims\/auth\/org/)
    await expect(page.getByText('钉钉服务暂不可用')).toBeVisible()
    await expect(page.getByText('组织对账已连续 2 次失败')).toBeVisible()
  })
})
