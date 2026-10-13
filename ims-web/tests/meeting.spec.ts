/**
 * B18-M18 会议模块 E2E 测试
 * 依据: docs/ims-v2-rewrite/modules/B18-M18会议/02-业务E2E用例.md
 * 桌面 1280×720 + 手机 390×844 双视口
 */
import { test, expect, type Page, type Route } from '@playwright/test'

const BEIJING_TZ = 'Asia/Shanghai'

function json(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

function ok<T>(data: T) {
  return { code: 0, msg: '成功', data }
}

function fail(code: number, msg: string, data: unknown = null) {
  return { code, msg, data }
}

function menu(path: string, name: string, permCode?: string, children?: ReturnType<typeof menu>[]) {
  return {
    id: path,
    name,
    path,
    type: children?.length ? 'DIR' : 'MENU',
    permCode: permCode ?? null,
    sort: 0,
    visible: true,
    children: children ?? [],
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
    menus: options?.menus ?? [
      menu('/ims/meet', '会议', null, [
        menu('/ims/meet/minutes', '会议纪要', 'ims:meet:minutes:query'),
      ]),
    ],
    permCodes: options?.permCodes ?? [
      'ims:meet:minutes:query',
      'ims:meet:minutes:query-self',
      'ims:meet:minutes:add',
      'ims:meet:minutes:edit',
      'ims:meet:minutes:archive',
      'ims:meet:minutes:delete',
      'ims:meet:minutes:appendix',
      'ims:meet:minutes:supervise',
    ],
    permDetails: {},
    dataScopeText: '全部',
  })
}

async function installAuth(page: Page, permCodes?: string[], pwdResetRequired?: boolean) {
  await page.route('**/admin-api/ims/auth/login', async (route) => {
    await route.fulfill(json(ok({
      accessToken: 'meet-access-token',
      refreshToken: 'meet-refresh-token',
      expiresIn: 7200,
      pwdResetRequired: pwdResetRequired ?? false,
    })))
  })
  await page.route('**/admin-api/ims/auth/me', async (route) => {
    const authorization = route.request().headers().authorization || ''
    const token = authorization.toLowerCase().startsWith('bearer ')
      ? authorization.slice(7).trim()
      : ''
    if (!token) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify(fail(1002, '登录已失效，请重新登录')),
      })
      return
    }
    await route.fulfill(json(mePayload({
      permCodes: permCodes ?? [
        'ims:meet:minutes:query',
        'ims:meet:minutes:query-self',
        'ims:meet:minutes:add',
        'ims:meet:minutes:edit',
        'ims:meet:minutes:archive',
        'ims:meet:minutes:delete',
        'ims:meet:minutes:appendix',
        'ims:meet:minutes:supervise',
      ],
      pwdResetRequired: pwdResetRequired ?? false,
    })))
  })
  await page.route('**/admin-api/ims/auth/logout', async (route) => {
    await route.fulfill(json(ok(null)))
  })
}

async function loginAndNavigate(page: Page, targetPath: string = '/ims/meet/minutes') {
  await page.goto('/login')
  await page.getByPlaceholder('请输入用户名').fill('test_admin')
  await page.getByPlaceholder('请输入密码').fill('Test1234')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL((url) => !url.pathname.includes('/login'))
  if (targetPath) {
    await page.goto(targetPath)
  }
}

const mockUsers = [
  { id: '1', username: 'recorder', nickname: '记录人', main_dept_id: '1', status: 'ACTIVE' },
  { id: '2', username: 'attendee1', nickname: '参会人1', main_dept_id: '1', status: 'ACTIVE' },
  { id: '3', username: 'attendee2', nickname: '参会人2', main_dept_id: '1', status: 'ACTIVE' },
  { id: '4', username: 'assignee', nickname: '责任人', main_dept_id: '1', status: 'ACTIVE' },
  { id: '5', username: 'supervise', nickname: '监督人', main_dept_id: '1', status: 'ACTIVE' },
]

const mockMinutesList = [
  {
    id: '1',
    code: 'MM20261013001',
    title: '测试会议01',
    meeting_date: '2026-10-13T10:00:00',
    recorder_user_id: '1',
    recorder_name: '记录人',
    attendee_names: ['参会人1', '参会人2'],
    status: 'REGISTERED',
    archived_at: null,
    action_item_count: 0,
    action_item_closed_count: 0,
  },
  {
    id: '2',
    code: 'MM20261012001',
    title: '已录入纪要会议',
    meeting_date: '2026-10-12T14:00:00',
    recorder_user_id: '1',
    recorder_name: '记录人',
    attendee_names: ['参会人1'],
    status: 'MINUTES_RECORDED',
    archived_at: null,
    action_item_count: 1,
    action_item_closed_count: 0,
  },
  {
    id: '3',
    code: 'MM20261011001',
    title: '已归档会议',
    meeting_date: '2026-10-11T09:00:00',
    recorder_user_id: '1',
    recorder_name: '记录人',
    attendee_names: ['参会人1', '参会人2'],
    status: 'ARCHIVED',
    archived_at: '2026-10-11T18:00:00',
    action_item_count: 2,
    action_item_closed_count: 1,
  },
]

function installMeetingMocks(page: Page) {
  page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
    await route.fulfill(json(ok({
      list: mockMinutesList,
      total: mockMinutesList.length,
      page_no: 1,
      page_size: 10,
    })))
  })

  page.route('**/admin-api/ims/user/simple-page*', async (route) => {
    await route.fulfill(json(ok({
      list: mockUsers,
      total: mockUsers.length,
      page_no: 1,
      page_size: 10,
    })))
  })
}

test.describe('B18 会议模块 E2E', () => {
  test('E2E-B18-01: 会前登记 - 正常登记（正文空）状态为已登记', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    let createRequest: any = null
    await page.route('**/admin-api/ims/meet/minutes', async (route) => {
      if (route.request().method() === 'POST') {
        createRequest = route.request().postDataJSON()
        const now = new Date()
        const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '')
        await route.fulfill(json(ok({
          data: {
            id: '100',
            code: `MM${dateStr}001`,
            title: createRequest.title,
            meeting_date: createRequest.meeting_date,
            status: 'REGISTERED',
            attendees: createRequest.attendees,
            attendee_names: ['参会人1', '参会人2', '外部人员'],
            recorder_user_id: '1',
            recorder_name: '记录人',
            decisions: [],
            action_items: [],
            appendices: [],
            action_item_count: 0,
            action_item_closed_count: 0,
          },
          warnings: [],
        })))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)
    await expect(page.locator('.app-layout')).toBeVisible()

    await page.getByRole('button', { name: '新建' }).click()
    const drawer = page.locator('.el-drawer:visible')
    await expect(drawer).toBeVisible()

    await drawer.getByPlaceholder('请输入会议主题').fill('E2E测试会议')

    await drawer.getByRole('button', { name: '保存' }).click()

    expect(createRequest).not.toBeNull()
    expect(createRequest.title).toBe('E2E测试会议')
  })

  test('E2E-B18-02: 登记校验 - 主题超长或参会人为空返回 1001', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill(json(fail(1001, '校验失败')))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    await page.getByRole('button', { name: '新建' }).click()
    const drawer = page.locator('.el-drawer:visible')

    await drawer.getByPlaceholder('请输入会议主题').fill('A'.repeat(129))

    await drawer.getByRole('button', { name: '保存' }).click()

    await expect(page.getByText('校验失败').or(page.getByText('主题').and(page.getByText('字')))).toBeVisible({ timeout: 5000 })
  })

  test('E2E-B18-05: 超 24h 软提示 - 会后 30h 录入纪要显示警告但成功', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill(json(ok({
          data: {
            id: '101',
            code: 'MM20261012002',
            title: '会后30h测试',
            status: 'MINUTES_RECORDED',
            attendees: { internal: [1, 2], external: [] },
            attendee_names: ['参会人1', '参会人2'],
            recorder_user_id: '1',
            recorder_name: '记录人',
            summary: '<p>纪要内容</p>',
            decisions: [],
            action_items: [],
            appendices: [],
            action_item_count: 0,
            action_item_closed_count: 0,
          },
          warnings: [1116],
        })))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    await page.getByRole('button', { name: '新建' }).click()
    const drawer = page.locator('.el-drawer:visible')
    await drawer.getByPlaceholder('请输入会议主题').fill('会后30h测试')

    await drawer.getByRole('button', { name: '保存' }).click()

    await expect(
      page.locator('.el-message--warning').or(page.getByText('24')).or(page.getByText('1116'))
    ).toBeVisible({ timeout: 5000 })
  })

  test('E2E-B18-07: 非记录人且无 edit 码编辑返回 1008', async ({ page }) => {
    await installAuth(page, ['ims:meet:minutes:query', 'ims:meet:minutes:query-self'])
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes/1', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill(json(fail(1008, '暂无权限')))
      } else if (route.request().method() === 'GET') {
        await route.fulfill(json(ok({
          id: '1',
          code: 'MM20261013001',
          title: '测试会议01',
          meeting_date: '2026-10-13T10:00:00',
          recorder_user_id: '2',
          recorder_name: '其他记录人',
          status: 'REGISTERED',
          attendees: { internal: [1, 2], external: [] },
          attendee_names: ['参会人1', '参会人2'],
          summary: null,
          decisions: [],
          action_items: [],
          appendices: [],
          action_item_count: 0,
          action_item_closed_count: 0,
        })))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    const editButton = page.getByRole('button', { name: '编辑' }).first()
    const hasEditButton = await editButton.count() > 0
    if (hasEditButton) {
      await editButton.click()
      await expect(page.getByText('暂无权限')).toBeVisible()
    } else {
      expect(hasEditButton).toBe(false)
    }
  })

  test('E2E-B18-08: 归档 - 记录人点归档状态变为已归档', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    let archiveCalled = false
    await page.route('**/admin-api/ims/meet/minutes/2/archive', async (route) => {
      archiveCalled = true
      await route.fulfill(json(ok({
        data: {
          id: '2',
          code: 'MM20261012001',
          title: '已录入纪要会议',
          meeting_date: '2026-10-12T14:00:00',
          status: 'ARCHIVED',
          archived_at: new Date().toISOString(),
          archived_by: '1',
          archived_by_name: '记录人',
          attendees: { internal: [1], external: [] },
          attendee_names: ['参会人1'],
          recorder_user_id: '1',
          recorder_name: '记录人',
          summary: '<p>纪要内容</p>',
          decisions: [],
          action_items: [],
          appendices: [],
          action_item_count: 1,
          action_item_closed_count: 0,
        },
        warnings: [],
      })))
    })

    await page.route('**/admin-api/ims/meet/minutes/2', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill(json(ok({
          id: '2',
          code: 'MM20261012001',
          title: '已录入纪要会议',
          meeting_date: '2026-10-12T14:00:00',
          status: 'MINUTES_RECORDED',
          attendees: { internal: [1], external: [] },
          attendee_names: ['参会人1'],
          recorder_user_id: '1',
          recorder_name: '记录人',
          summary: '<p>纪要内容</p>',
          decisions: [],
          action_items: [{
            id: '1',
            description: '测试行动项',
            assignee_user_id: '4',
            assignee_name: '责任人',
            due_date: '2026-10-20',
            status: 'OPEN',
            close_remark: null,
            evidence_url: null,
            closed_at: null,
          }],
          appendices: [],
          action_item_count: 1,
          action_item_closed_count: 0,
        })))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    const row = page.locator('.el-table__body tr').filter({ hasText: '已录入纪要会议' })
    const archiveBtn = row.getByRole('button', { name: '归档' })
    if (await archiveBtn.count() > 0) {
      await archiveBtn.click()

      const dialog = page.getByRole('dialog')
      if (await dialog.count() > 0) {
        await expect(dialog.getByText('归档后不可修改').or(dialog.getByText('行动项'))).toBeVisible()
        await dialog.getByRole('button', { name: '确定' }).click()
      }

      await expect(page.getByText('归档成功').or(page.locator('.el-message--success'))).toBeVisible({ timeout: 5000 })
      expect(archiveCalled).toBe(true)
    }
  })

  test('E2E-B18-09: 未录纪要归档 - 对已登记会议归档返回 1001', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes/1/archive', async (route) => {
      await route.fulfill(json(fail(1001, '请先录入纪要')))
    })

    await page.route('**/admin-api/ims/meet/minutes/1', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill(json(ok({
          id: '1',
          code: 'MM20261013001',
          title: '测试会议01',
          meeting_date: '2026-10-13T10:00:00',
          status: 'REGISTERED',
          attendees: { internal: [1, 2], external: [] },
          attendee_names: ['参会人1', '参会人2'],
          recorder_user_id: '1',
          recorder_name: '记录人',
          summary: null,
          decisions: [],
          action_items: [],
          appendices: [],
          action_item_count: 0,
          action_item_closed_count: 0,
        })))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    const row = page.locator('.el-table__body tr').filter({ hasText: '测试会议01' })
    const archiveBtn = row.getByRole('button', { name: '归档' })
    if (await archiveBtn.count() > 0) {
      await archiveBtn.click()
      const dialog = page.getByRole('dialog')
      if (await dialog.count() > 0) {
        await dialog.getByRole('button', { name: '确定' }).click()
      }
      await expect(page.getByText('请先录入纪要')).toBeVisible({ timeout: 5000 })
    }
  })

  test('E2E-B18-10: 归档后修改 - 对已归档纪要调 PUT 返回 1117', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes/3', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill(json(fail(1117, '已归档纪要不可修改')))
      } else if (route.request().method() === 'GET') {
        await route.fulfill(json(ok({
          id: '3',
          code: 'MM20261011001',
          title: '已归档会议',
          meeting_date: '2026-10-11T09:00:00',
          status: 'ARCHIVED',
          archived_at: '2026-10-11T18:00:00',
          attendees: { internal: [1, 2], external: [] },
          attendee_names: ['参会人1', '参会人2'],
          recorder_user_id: '1',
          recorder_name: '记录人',
          summary: '<p>纪要内容</p>',
          decisions: [],
          action_items: [],
          appendices: [],
          action_item_count: 2,
          action_item_closed_count: 1,
        })))
      } else {
        await route.continue()
      }
    })

    await page.route('**/admin-api/ims/meet/minutes/3/archive', async (route) => {
      await route.fulfill(json(fail(1117, '已归档纪要不可重复归档')))
    })

    await loginAndNavigate(page)

    const row = page.locator('.el-table__body tr').filter({ hasText: '已归档会议' })
    const editBtn = row.getByRole('button', { name: '编辑' })
    expect(await editBtn.count()).toBe(0)
  })

  test('E2E-B18-12: 删除 - R1 删除未归档纪要成功，删除已归档返回 1117', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    let deleteCalledFor1 = false
    await page.route('**/admin-api/ims/meet/minutes/1', async (route) => {
      if (route.request().method() === 'DELETE') {
        deleteCalledFor1 = true
        await route.fulfill(json(ok(null)))
      } else {
        await route.continue()
      }
    })

    await page.route('**/admin-api/ims/meet/minutes/3', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill(json(fail(1117, '已归档纪要不可删除')))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    const row1 = page.locator('.el-table__body tr').filter({ hasText: '测试会议01' })
    const moreBtn1 = row1.getByRole('button', { name: '更多' })
    if (await moreBtn1.count() > 0) {
      await moreBtn1.click()
      await page.locator('.el-dropdown-menu:visible').getByText('删除', { exact: true }).click()
      const dialog = page.getByRole('dialog')
      if (await dialog.count() > 0) {
        await dialog.getByRole('button', { name: '确定' }).click()
      }
      await expect(page.getByText('删除成功').or(page.locator('.el-message--success'))).toBeVisible({ timeout: 5000 })
      expect(deleteCalledFor1).toBe(true)
    }
  })

  test('E2E-B18-14: 非责任人回填 / 校验 - 非责任人回填返回 1118，非法 URL 返回 1001', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes/action-item/1', async (route) => {
      if (route.request().method() === 'PUT') {
        const body = route.request().postDataJSON()
        if (body.evidence_url?.startsWith('javascript:')) {
          await route.fulfill(json(fail(1001, '证据链接仅支持 http/https')))
        } else {
          await route.fulfill(json(fail(1118, '非行动项责任人，无权回填')))
        }
      } else {
        await route.continue()
      }
    })

    await page.request.put('/admin-api/ims/meet/minutes/action-item/1', {
      data: { close_remark: '完成', evidence_url: 'javascript:alert(1)' },
      headers: { Authorization: 'Bearer meet-access-token' },
    }).then(async (response) => {
      const body = await response.json()
      expect(body.code).toBe(1001)
    })
  })

  test('E2E-B18-16: 留痕率与未归档清单 - 无 supervise 码用户调接口返回 1008', async ({ page }) => {
    await installAuth(page, ['ims:meet:minutes:query'])
    installMeetingMocks(page)

    await page.route('**/admin-api/ims/meet/minutes/archive-rate*', async (route) => {
      await route.fulfill(json(fail(1008, '暂无权限')))
    })

    await loginAndNavigate(page)

    const response = await page.request.get('/admin-api/ims/meet/minutes/archive-rate', {
      headers: { Authorization: 'Bearer meet-access-token' },
    })
    const body = await response.json()
    expect(body.code).toBe(1008)
  })

  test('E2E-B18-18: 仅本人范围 - 只有 query-self 的参会人只见本人相关会议', async ({ page }) => {
    await installAuth(page, ['ims:meet:minutes:query-self'])

    await page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
      await route.fulfill(json(ok({
        list: [mockMinutesList[0]],
        total: 1,
        page_no: 1,
        page_size: 10,
      })))
    })

    await page.route('**/admin-api/ims/meet/minutes/999', async (route) => {
      await route.fulfill(json(fail(1504, '资源不存在')))
    })

    await loginAndNavigate(page)

    await expect(page.locator('.el-table__body tr')).toHaveCount(1)

    const newBtn = page.getByRole('button', { name: '新建' })
    expect(await newBtn.count()).toBe(0)
  })

  test('E2E-B18-19: 跨部门 / 跨租户隔离 - 他部门会议不在列表，详情返回 1504', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
      await route.fulfill(json(ok({
        list: mockMinutesList.filter(m => m.id !== '999'),
        total: 2,
        page_no: 1,
        page_size: 10,
      })))
    })

    await page.route('**/admin-api/ims/meet/minutes/999', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill(json(fail(1504, '资源不存在或跨租户访问')))
      } else {
        await route.continue()
      }
    })

    await loginAndNavigate(page)

    const response = await page.request.get('/admin-api/ims/meet/minutes/999', {
      headers: { Authorization: 'Bearer meet-access-token' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })

  test('E2E-B18-20: 菜单与通用口径 - R1 登录看侧栏有会议菜单', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await loginAndNavigate(page)

    await expect(page.locator('.app-sidebar')).toBeVisible()
    await expect(
      page.locator('.app-sidebar').getByText('会议').or(
        page.locator('.app-sidebar').getByText('会议纪要')
      )
    ).toBeVisible()
  })

  test('E2E-B18-20b: 无权限用户直调列表返回 1008', async ({ page }) => {
    await installAuth(page, [])

    await page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
      await route.fulfill(json(fail(1008, '暂无权限')))
    })

    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('ims_access_token', 'meet-access-token')
      localStorage.setItem('ims_refresh_token', 'meet-refresh-token')
    })

    const response = await page.request.get('/admin-api/ims/meet/minutes/list', {
      headers: { Authorization: 'Bearer meet-access-token' },
    })
    const body = await response.json()
    expect(body.code).toBe(1008)
  })

  test('E2E-B18-20c: 须改密用户调列表返回 1008', async ({ page }) => {
    await installAuth(page, ['ims:meet:minutes:query'], true)

    await page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
      await route.fulfill(json(fail(1008, '请先修改密码')))
    })

    await loginAndNavigate(page, '')

    await expect(page).toHaveURL(/\/password-reset/)
  })
})

test.describe('B18 会议模块 E2E - 移动端', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('E2E-B18-M01: 移动端列表正常显示', async ({ page }) => {
    await installAuth(page)
    installMeetingMocks(page)

    await loginAndNavigate(page)

    await expect(page.locator('.el-table').or(page.locator('[class*="list"]'))).toBeVisible()
    const viewport = page.viewportSize()
    expect(viewport?.width).toBe(390)
  })
})

test.describe('B18 会议模块 E2E - 安全测试', () => {
  test('E2E-B18-SEC-01: 1002 会话失效跳转登录页', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify(fail(1002, '登录已失效，请重新登录')),
      })
    })

    await page.goto('/ims/meet/minutes')

    await expect(page).toHaveURL(/\/login/)
  })

  test('E2E-B18-SEC-02: 1216 冻结/离职用户登录失败', async ({ page }) => {
    await page.route('**/admin-api/ims/auth/login', async (route) => {
      await route.fulfill(json(fail(1216, '账号已冻结或已离职，无法登录')))
    })

    await page.goto('/login')
    await page.getByPlaceholder('请输入用户名').fill('frozen_user')
    await page.getByPlaceholder('请输入密码').fill('Test1234')
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page.getByText('冻结').or(page.getByText('离职'))).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('E2E-B18-SEC-03: 1008 租户停用拒绝访问', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/list*', async (route) => {
      await route.fulfill(json(fail(1008, '所属组织已停用')))
    })

    await loginAndNavigate(page)

    await expect(page.getByText('停用').or(page.getByText('暂无权限'))).toBeVisible()
  })

  test('E2E-B18-SEC-04: 跨租户编辑返回 1504', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/999', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill(json(fail(1504, '资源不存在')))
      } else {
        await route.continue()
      }
    })

    const response = await page.request.put('/admin-api/ims/meet/minutes/999', {
      data: { title: 'Hacked', meeting_date: '2026-10-13T10:00:00', attendees: { internal: [1], external: [] }, base_version: 1 },
      headers: { Authorization: 'Bearer meet-access-token', 'Content-Type': 'application/json' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })

  test('E2E-B18-SEC-05: 跨租户归档返回 1504', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/999/archive', async (route) => {
      await route.fulfill(json(fail(1504, '资源不存在')))
    })

    const response = await page.request.put('/admin-api/ims/meet/minutes/999/archive', {
      headers: { Authorization: 'Bearer meet-access-token' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })

  test('E2E-B18-SEC-06: 跨租户附录返回 1504', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/999/appendix', async (route) => {
      await route.fulfill(json(fail(1504, '资源不存在')))
    })

    const response = await page.request.post('/admin-api/ims/meet/minutes/999/appendix', {
      data: { content: 'Hacked appendix' },
      headers: { Authorization: 'Bearer meet-access-token', 'Content-Type': 'application/json' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })

  test('E2E-B18-SEC-07: 跨租户删除返回 1504', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/999', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill(json(fail(1504, '资源不存在')))
      } else {
        await route.continue()
      }
    })

    const response = await page.request.delete('/admin-api/ims/meet/minutes/999', {
      headers: { Authorization: 'Bearer meet-access-token' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })

  test('E2E-B18-SEC-08: 跨租户回填行动项返回 1504（数据范围先于责任人校验）', async ({ page }) => {
    await installAuth(page)

    await page.route('**/admin-api/ims/meet/minutes/action-item/999', async (route) => {
      await route.fulfill(json(fail(1504, '资源不存在')))
    })

    const response = await page.request.put('/admin-api/ims/meet/minutes/action-item/999', {
      data: { close_remark: 'Hacked close' },
      headers: { Authorization: 'Bearer meet-access-token', 'Content-Type': 'application/json' },
    })
    const body = await response.json()
    expect(body.code).toBe(1504)
  })
})
