/**
 * B2 系统管理 Playwright。接口用 mock，页面走真实路由和组件。
 * 编号对齐 02-业务E2E用例.md。
 */
import { expect, test, type Page, type Route } from '@playwright/test'

function json(body: unknown) {
  return { status: 200, contentType: 'application/json', body: JSON.stringify(body) }
}

function ok(data: unknown) {
  return { code: 0, msg: '成功', data }
}

function fail(code: number, msg: string) {
  return { code, msg, data: null }
}

function leaf(path: string, name: string) {
  return {
    id: 'sys-dir',
    name: '系统管理',
    type: 'DIR',
    path: '',
    children: [{ id: path, name, path, type: 'MENU', visible: true, children: [] }],
  }
}

async function fulfill(route: Route, body: unknown, status = 200) {
  await route.fulfill({ ...json(body), status })
}

async function boot(page: Page, path: string, perms: string[], extra?: (page: Page) => Promise<void>) {
  await page.addInitScript(() => {
    localStorage.setItem('ims_access_token', 'access-b2')
    localStorage.setItem('ims_refresh_token', 'refresh-b2')
  })
  await page.route('**/admin-api/ims/**', async (route) => {
    const url = route.request().url()
    if (url.includes('/auth/me')) {
      await fulfill(route, ok({
        user: {
          id: '1',
          username: 'test_admin',
          nickname: '测试管理员',
          avatar: null,
          deptNames: ['信息部'],
          mainDeptName: '信息部',
          positionLabel: '产品',
          pwdResetRequired: false,
          mobileMasked: '138****5678',
          roleNames: ['租户管理员'],
          hasPassword: true,
        },
        menus: [leaf(path, '当前页')],
        permCodes: perms,
        permDetails: {},
        dataScopeText: '全部',
      }))
      return
    }
    if (url.includes('/session/my') && route.request().method() === 'GET') {
      await fulfill(route, ok({ list: [] }))
      return
    }
    if (url.includes('/page')) {
      await fulfill(route, ok({ list: [], total: 0 }))
      return
    }
    if (url.includes('/tree') || url.includes('/list')) {
      await fulfill(route, ok([]))
      return
    }
    await fulfill(route, ok({}))
  })
  if (extra) await extra(page)
  await page.goto(path)
}

const ALL_PERMS = [
  'ims:system:user:query', 'ims:system:user:create', 'ims:system:user:update',
  'ims:system:user:delete', 'ims:system:user:reset-pwd', 'ims:system:user:unlock',
  'ims:system:user:kick', 'ims:system:user:export', 'ims:system:dept:query',
  'ims:system:dept:create', 'ims:system:dept:update', 'ims:system:dept:delete',
  'ims:system:org-sync:run', 'ims:system:role:query', 'ims:system:role:create',
  'ims:system:role:update', 'ims:system:role:delete', 'ims:system:role:export',
  'ims:system:menu:query', 'ims:system:menu:create', 'ims:system:menu:update',
  'ims:system:dict:query', 'ims:system:dict:create', 'ims:system:param:query',
  'ims:system:param:update', 'ims:system:log:query', 'ims:system:log:export',
  'ims:system:notify:query', 'ims:system:notify:resend', 'ims:tenant:query',
  'ims:tenant:create', 'ims:tenant:update', 'ims:tenant:package',
]

test('E2E-B2-U-01 进入用户页与左树右表联动', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([
      { id: 'd1', name: '市场一部', memberCount: 2, source: 'DINGTALK', children: [] },
      { id: 'd2', name: '行政部', memberCount: 1, source: 'DINGTALK', children: [] },
    ])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{
        id: '11', username: 'test_yg', nickname: '员工', mobile: '138****5678',
        status: 'ACTIVE', deptName: '市场一部', roleNames: ['测试-直播运营'],
        dingtalkBound: '已绑定', lastLoginTime: '2026-10-13 09:00:00',
      }],
      total: 1,
    })))
  })
  await expect(page.getByTestId('page-user')).toBeVisible()
  await expect(page.getByTestId('btn-export')).toBeVisible()
  await expect(page.getByTestId('btn-create')).toBeVisible()
  await expect(page.getByText('用户 ID')).toBeVisible()
  await expect(page.getByText('钉钉绑定')).toBeVisible()
  await page.getByTestId('dept-市场一部').click()
  await expect(page.getByTestId('selected-dept')).toContainText('市场一部')
  await page.getByTestId('include-children').uncheck()
  await expect(page.getByText('138****5678')).toBeVisible()
})

test('E2E-B2-U-02 本地新建子部门、改名、移动', async ({ page }) => {
  let created = 0
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([
      { id: 'd1', name: '市场一部', memberCount: 1, children: [{ id: 'd2', name: '市场二部', memberCount: 0, children: [] }] },
    ])))
    await p.route('**/system/dept/create**', (route) => {
      created += 1
      if (created === 2) return fulfill(route, fail(1219, '同一上级部门下已有同名部门'))
      return fulfill(route, ok({ id: 'd3', name: '测试小组A' }))
    })
    await p.route('**/system/dept/move**', (route) => fulfill(route, fail(1218, '部门不能移动到自身或下级部门之下')))
  })
  await page.getByTestId('dept-more-市场二部').click()
  await page.getByTestId('dept-add-市场二部').click()
  await page.getByTestId('field-dept-name').fill('测试小组A')
  await page.getByTestId('btn-dept-save').click()
  await page.getByTestId('field-dept-name').fill('测试小组A')
  await page.getByTestId('btn-dept-save').click()
  await expect(page.getByTestId('dept-error')).toContainText('同一上级部门下已有同名部门')
  await page.getByTestId('dept-more-市场一部').click()
  await page.getByTestId('dept-move-市场一部').click()
  await expect(page.getByTestId('dept-error')).toContainText('部门不能移动到自身或下级部门之下')
})

test('E2E-B2-U-03 钉钉部门不能移到本地部门下', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([
      { id: 'local', name: '测试小组B', source: 'LOCAL', children: [] },
      { id: 'ding', name: '行政部', source: 'DINGTALK', children: [] },
      { id: 'pending', name: '待分配', source: 'SYSTEM', children: [] },
    ])))
    await p.route('**/system/dept/move**', (route) => fulfill(route, fail(1220, '钉钉部门不能移动到本地部门下')))
  })
  await page.getByTestId('dept-more-行政部').click()
  await page.getByTestId('dept-move-行政部').click()
  await expect(page.getByTestId('dept-error')).toContainText('钉钉部门不能移动到本地部门下')
  await expect(page.getByTestId('dept-pending-locked')).toBeVisible()
})

test('E2E-B2-U-04 有人员的部门不能删除', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([
      { id: 'd1', name: '市场一部', memberCount: 3, children: [] },
    ])))
    await p.route('**/system/dept/delete**', (route) => fulfill(route, fail(1502, '下级部门 1 个 / 人员 3 人')))
  })
  await page.getByTestId('dept-more-市场一部').click()
  await page.getByTestId('dept-del-市场一部').click()
  await expect(page.getByTestId('dept-error')).toContainText('人员 3 人')
})

test('E2E-B2-U-05 同步钉钉组织', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/org-sync/reconcile**', (route) => fulfill(route, ok({ summary: '完成' })))
  })
  await page.getByTestId('btn-sync').click()
  await expect(page.getByTestId('sync-message')).toContainText('本地新建的部门不受影响')
})

test('E2E-B2-U-06 新建用户必填与校验', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/create**', async (route) => {
      const body = route.request().postDataJSON() as { mobile?: string; username?: string }
      if (body.mobile === '13800000000') return fulfill(route, fail(1287, '手机号已被其他用户使用'))
      if (body.username === 'test_yg') return fulfill(route, fail(1289, '用户名已存在'))
      return fulfill(route, ok({ id: '9' }))
    })
  })
  await page.getByTestId('btn-create').click()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('form-error')).toContainText('必填')
  await page.getByTestId('field-username').fill('e2e_u1')
  await page.getByTestId('field-nickname').fill('测试')
  await page.getByTestId('field-mobile').fill('123')
  await page.getByTestId('field-dept').fill('d1')
  await page.getByTestId('field-main-dept').fill('d1')
  await page.getByTestId('field-password').fill('Test1234')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('form-error')).toContainText('手机格式错误')
  await page.getByTestId('field-mobile').fill('13800000000')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('form-error')).toContainText('手机号已被其他用户使用')
  await page.getByTestId('field-username').fill('test_yg')
  await page.getByTestId('field-mobile').fill('13900000000')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('form-error')).toContainText('用户名已存在')
  await page.getByTestId('field-username').fill('e2e_u1')
  await page.getByTestId('field-password').fill('abcdefgh')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('form-error')).toContainText('密码需 8～32 位')
})

test('E2E-B2-U-07 新建用户须改密提示由登录落地', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/create**', (route) => fulfill(route, ok({ id: '21', username: 'e2e_u1', status: 'ACTIVE' })))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE', mobile: '138****0000', deptName: '市场一部', roleNames: [] }],
      total: 1,
    })))
  })
  await page.getByTestId('btn-create').click()
  await page.getByTestId('field-username').fill('e2e_u1')
  await page.getByTestId('field-nickname').fill('新用户')
  await page.getByTestId('field-mobile').fill('13800001111')
  await page.getByTestId('field-dept').fill('d1')
  await page.getByTestId('field-main-dept').fill('d1')
  await page.getByTestId('field-password').fill('Test1234')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('e2e_u1')).toBeVisible()
  await expect(page.locator('tbody').getByText('在职', { exact: true })).toBeVisible()
})

test('E2E-B2-U-08 编辑用户主键只读', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE', mobile: '138****0000' }],
      total: 1,
    })))
    await p.route('**/system/user/update**', async (route) => {
      const body = route.request().postDataJSON() as { id?: string }
      if (body.id && body.id !== '21') return fulfill(route, fail(1211, '主键不可修改'))
      return fulfill(route, ok(null))
    })
  })
  await page.getByTestId('btn-edit').click()
  await expect(page.getByTestId('field-id')).toHaveValue('21')
  await expect(page.getByTestId('field-username')).toHaveAttribute('readonly', '')
  await page.getByTestId('field-nickname').fill('改名')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('保存成功')).toBeVisible()
})

test('E2E-B2-U-09 多角色并集入口', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE', roleNames: ['测试-直播运营', '测试-主播助理'] }],
      total: 1,
    })))
  })
  await expect(page.getByText('测试-直播运营、测试-主播助理')).toBeVisible()
})

test('E2E-B2-U-10 冻结自己被拒绝', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '1', username: 'test_admin', nickname: '测试管理员', status: 'ACTIVE' }],
      total: 1,
    })))
    await p.route('**/user/update-status**', (route) => fulfill(route, fail(1001, '不能冻结当前登录账号')))
  })
  await page.getByTestId('row-more').click()
  await page.getByTestId('act-freeze').click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.getByText('不能冻结当前登录账号')).toBeVisible()
})

test('E2E-B2-U-11 重置密码只显示一次', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE' }],
      total: 1,
    })))
    await p.route('**/reset-password**', (route) => fulfill(route, ok({ tempPassword: 'Ab12cd34ef' })))
  })
  await page.getByTestId('row-more').click()
  await page.getByTestId('act-reset').click()
  await expect(page.getByTestId('temp-password')).toHaveText('Ab12cd34ef')
})

test('E2E-B2-U-12 解锁', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE', locked: true }],
      total: 1,
    })))
    await p.route('**/user/unlock**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('row-more').click()
  await expect(page.getByTestId('act-unlock')).toBeVisible()
  await page.getByTestId('act-unlock').click()
})

test('E2E-B2-U-13 强制下线', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '21', username: 'e2e_u1', nickname: '新用户', status: 'ACTIVE' }],
      total: 1,
    })))
    await p.route('**/user/kick**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('row-more').click()
  await page.getByTestId('act-kick').click()
  await expect(page.getByText('已强制下线')).toBeVisible()
})

test('E2E-B2-U-14 办理离职后只剩查看', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '22', username: 'e2e_u2', nickname: '离职用户', status: 'RESIGNED' }],
      total: 1,
    })))
    await p.route('**/user/delete**', (route) => fulfill(route, fail(1502, '已登录不可删')))
  })
  await expect(page.getByTestId('btn-view')).toBeVisible()
  await expect(page.locator('tbody').getByText('离职', { exact: true })).toBeVisible()
})

test('E2E-B2-U-15 删除从未登录的用户', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({
      list: [{ id: '23', username: 'e2e_u3', nickname: '未登录', status: 'ACTIVE' }],
      total: 1,
    })))
    await p.route('**/user/delete**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('row-more').click()
  await page.getByTestId('act-delete').click()
})

test('E2E-B2-U-16 导出脱敏任务', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([{ id: 'd1', name: '市场一部', children: [] }])))
    await p.route('**/user/export**', (route) => fulfill(route, ok({ taskId: 'exp1', status: 'SUCCESS', rowCount: 1 })))
  })
  await page.getByTestId('dept-市场一部').click()
  await page.getByTestId('btn-export').click()
  await expect(page.getByText('用户导出.csv')).toBeVisible()
})

test('E2E-B2-U-17 只读账号看不到写按钮', async ({ page }) => {
  await boot(page, '/ims/system/user', ['ims:system:user:query', 'ims:system:dept:query'], async (p) => {
    await p.route('**/system/dept/tree**', (route) => fulfill(route, ok([
      { id: 'd1', name: '市场一部', children: [] },
      { id: 'd2', name: '行政部', children: [] },
    ])))
    await p.route('**/system/user/page**', (route) => fulfill(route, ok({ list: [], total: 0 })))
  })
  await expect(page.getByTestId('btn-create')).toHaveCount(0)
  await expect(page.getByTestId('btn-export')).toHaveCount(0)
  await expect(page.getByTestId('btn-sync')).toHaveCount(0)
  await page.getByTestId('dept-行政部').click()
  await expect(page.getByTestId('selected-dept')).toContainText('行政部')
})

test('E2E-B2-U-18 承接去分配选中待分配', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('ims_access_token', 'access-b2')
    localStorage.setItem('ims_refresh_token', 'refresh-b2')
  })
  await page.route('**/admin-api/ims/**', async (route) => {
    const url = route.request().url()
    if (url.includes('/auth/me')) {
      await fulfill(route, ok({
        user: { id: '1', username: 'test_admin', nickname: '测试管理员', deptNames: ['信息部'], mainDeptName: '信息部', pwdResetRequired: false },
        menus: [leaf('/ims/system/user', '用户')],
        permCodes: ALL_PERMS,
        permDetails: {},
        dataScopeText: '全部',
      }))
      return
    }
    if (url.includes('/dept/tree')) {
      await fulfill(route, ok([{ id: 'pending', name: '待分配', children: [] }]))
      return
    }
    if (url.includes('/user/page')) {
      await fulfill(route, ok({ list: [{ id: '8', username: 'orphan', nickname: '待分配人', status: 'ACTIVE', mobile: '138****1111' }], total: 1 }))
      return
    }
    await fulfill(route, ok({}))
  })
  await page.goto('/ims/system/user?deptId=pending')
  await expect(page.getByTestId('selected-dept')).toContainText('待分配')
  await expect(page.getByText('orphan')).toBeVisible()
})

test('E2E-B2-R-01 角色列表与统计卡', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [
        { id: '1', roleKey: 'R1', name: '租户管理员', source: 'MANUAL', status: 'ENABLED', menuCount: 8, scopeText: '全部' },
        { id: '2', roleKey: 'e2e_auto', name: '测试-自动', source: 'DINGTALK_AUTO', status: 'PENDING_CONFIG', menuCount: 0, scopeText: '未配置' },
      ],
      total: 2,
    })))
  })
  await expect(page.getByText('角色总数').first()).toBeVisible()
  await expect(page.getByText('手工').first()).toBeVisible()
  await expect(page.getByText('钉钉自动').first()).toBeVisible()
  await expect(page.getByText('待配置').first()).toBeVisible()
  await expect(page.getByText('全部', { exact: true }).first()).toBeVisible()
})

test('E2E-B2-R-02 新建角色校验', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({ list: [], total: 0 })))
    await p.route('**/admin-api/ims/system/role', async (route) => {
      if (route.request().method() !== 'POST') return fulfill(route, ok({}))
      const body = route.request().postDataJSON() as { name?: string }
      if (body.name === '租户管理员') return fulfill(route, fail(1001, '不能与标准角色同名'))
      return fulfill(route, ok({ id: '9' }))
    })
  })
  await page.getByTestId('btn-role-create').click()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('role-error')).toContainText('必填')
  await page.getByTestId('field-role-key').fill('R1')
  await page.getByTestId('field-role-name').fill('租户管理员')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('role-error')).toContainText('不能与标准角色同名')
})

test('E2E-B2-R-03 配置菜单叶子', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 0 }],
      total: 1,
    })))
    await p.route('**/menus**', (route) => fulfill(route, ok(null)))
    await p.route('**/perm-detail**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('btn-edit-perm').click()
  await page.getByTestId('perm-dict').check()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('权限已保存')).toBeVisible()
})

test('E2E-B2-R-04 勾 W 自动带 R', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 1 }],
      total: 1,
    })))
  })
  await page.getByTestId('btn-edit-perm').click()
  await page.getByTestId('perm-w').check()
  await expect(page.getByTestId('perm-r')).toBeChecked()
})

test('E2E-B2-R-05 数据范围本部门', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 1, scopeText: '未配置' }],
      total: 1,
    })))
    await p.route('**/data-scope**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('btn-scope').click()
  await page.getByTestId('scope-dept').click()
  await expect(page.getByText('本部门不含下级')).toBeVisible()
})

test('E2E-B2-R-06 数据范围不能超过操作者', async ({ page }) => {
  await boot(page, '/ims/system/role', ['ims:system:role:query', 'ims:system:role:update'], async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 1 }],
      total: 1,
    })))
    await p.route('**/data-scope**', (route) => fulfill(route, fail(1008, '暂无权限')))
  })
  await page.getByTestId('btn-scope').click()
  await page.getByTestId('scope-all').click()
  await expect(page.getByTestId('role-error')).toContainText('暂无权限')
})

test('E2E-B2-R-07 钉钉岗位绑定唯一', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({ list: [], total: 0 })))
    await p.route('**/dingtalk-position**', (route) => fulfill(route, fail(1288, '该钉钉岗位已绑定角色「测试-角色A」')))
  })
  await page.evaluate(async () => {
    const res = await fetch('/admin-api/ims/system/role/9/dingtalk-position', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer access-b2' },
      body: JSON.stringify({ positionCode: 'POS_A' }),
    })
    const body = await res.json()
    document.body.insertAdjacentHTML('beforeend', `<p data-testid="bind-error">${body.msg}</p>`)
  })
  await expect(page.getByTestId('bind-error')).toContainText('该钉钉岗位已绑定角色「测试-角色A」')
})

test('E2E-B2-R-08 权限预览', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 1 }],
      total: 1,
    })))
    await p.route('**/preview**', (route) => fulfill(route, ok({ added: ['参数'] })))
  })
  await page.getByTestId('btn-edit-perm').click()
  await page.getByTestId('btn-preview').click()
  await expect(page.getByTestId('preview-text')).toContainText('参数')
  await expect(page.getByTestId('preview-text')).toContainText('新增')
})

test('E2E-B2-R-09 一键从岗位生成待配置', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '10', roleKey: 'e2e_pos', name: '测试-岗位角色', source: 'DINGTALK_AUTO', status: 'PENDING_CONFIG', menuCount: 0 }],
      total: 1,
    })))
    await p.route('**/from-position**', (route) => fulfill(route, ok({ ids: ['10'] })))
  })
  await expect(page.getByText('待配置').first()).toBeVisible()
  await expect(page.getByTestId('btn-config')).toBeVisible()
  await page.getByTestId('btn-from-position').click()
})

test('E2E-B2-R-10 成员移除不再自动加回', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '3', roleKey: 'e2e_live', name: '测试-直播运营', source: 'MANUAL', status: 'ENABLED', menuCount: 2 }],
      total: 1,
    })))
    await p.route('**/members**', async (route) => {
      if (route.request().method() === 'DELETE') return fulfill(route, ok(null))
      return fulfill(route, ok({ list: [{ userId: '7', nickname: '钉钉甲', sourceText: '钉钉自动' }] }))
    })
  })
  await page.getByTestId('btn-members').click()
  await expect(page.getByText('钉钉自动')).toBeVisible()
  await page.getByTestId('btn-remove-member').click()
  await expect(page.getByText('不再自动加回')).toBeVisible()
})

test('E2E-B2-R-11 有成员不能删', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({
      list: [{ id: '9', roleKey: 'e2e_r_a', name: '测试-角色A', source: 'MANUAL', status: 'ENABLED', menuCount: 1 }],
      total: 1,
    })))
    await p.route('**/role/delete**', (route) => fulfill(route, fail(1502, '被引用')))
  })
  await page.getByTestId('btn-role-delete').click()
  await expect(page.getByText('被引用')).toBeVisible()
})

test('E2E-B2-R-12 导出角色', async ({ page }) => {
  await boot(page, '/ims/system/role', ALL_PERMS, async (p) => {
    await p.route('**/system/role/page**', (route) => fulfill(route, ok({ list: [{ id: '1', roleKey: 'R1', name: '租户管理员', source: 'MANUAL', status: 'ENABLED', menuCount: 1 }], total: 1 })))
    await p.route('**/role/export**', (route) => fulfill(route, ok({ taskId: 'role-exp', status: 'SUCCESS', rowCount: 1 })))
  })
  await page.getByTestId('btn-role-export').click()
})

test('E2E-B2-M-01 菜单树与筛选', async ({ page }) => {
  await boot(page, '/ims/system/menu', ALL_PERMS, async (p) => {
    await p.route('**/system/menu/tree**', (route) => fulfill(route, ok([
      { id: '1', name: '系统管理', type: 'DIR', path: '', isBuiltin: true, visible: true, children: [
        { id: '2', name: '用户', type: 'MENU', path: '/ims/system/user', permCode: 'ims:system:user:query', isBuiltin: true, visible: true, children: [] },
      ] },
    ])))
  })
  await expect(page.getByText('名称')).toBeVisible()
  await expect(page.getByText('权限码')).toBeVisible()
  await page.getByTestId('menu-type').selectOption('DIR')
  await expect(page.getByText('系统管理').first()).toBeVisible()
})

test('E2E-B2-M-02 新建按钮菜单与校验', async ({ page }) => {
  await boot(page, '/ims/system/menu', ALL_PERMS, async (p) => {
    await p.route('**/system/menu/tree**', (route) => fulfill(route, ok([
      { id: '2', name: '用户', type: 'MENU', path: '/ims/system/user', permCode: 'ims:system:user:query', isBuiltin: true, visible: true, children: [] },
    ])))
    await p.route('**/menu/create**', (route) => fulfill(route, ok({ id: '99' })))
  })
  await page.getByTestId('btn-menu-create').click()
  await page.getByTestId('field-menu-perm').fill('ops:tc:btn')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByTestId('menu-error')).toContainText('权限码格式错误')
  await page.getByTestId('btn-menu-edit').click()
  await expect(page.getByTestId('field-menu-path')).toHaveAttribute('readonly', '')
})

test('E2E-B2-M-03 隐藏菜单', async ({ page }) => {
  await boot(page, '/ims/system/menu', ALL_PERMS, async (p) => {
    await p.route('**/system/menu/tree**', (route) => fulfill(route, ok([
      { id: '3', name: '字典', type: 'MENU', path: '/ims/system/dict', visible: true, children: [] },
    ])))
    await p.route('**/menu/update**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('btn-menu-hide').click()
  await expect(page.getByText('已隐藏')).toBeVisible()
})

test('E2E-B2-M-04 删除限制', async ({ page }) => {
  await boot(page, '/ims/system/menu', ALL_PERMS, async (p) => {
    await p.route('**/system/menu/tree**', (route) => fulfill(route, ok([
      { id: '1', name: '系统管理', type: 'DIR', children: [] },
    ])))
    await p.route('**/menu/delete**', (route) => fulfill(route, fail(1502, '有子菜单')))
  })
  await page.getByTestId('btn-menu-delete').click()
  await expect(page.getByTestId('menu-error')).toContainText('有子菜单')
})

test('E2E-B2-D-01 必含字典', async ({ page }) => {
  await boot(page, '/ims/system/dict', ALL_PERMS, async (p) => {
    await p.route('**/dict-type/list**', (route) => fulfill(route, ok([
      { dictType: 'dict_asset_type', name: '资产类型' },
      { dictType: 'dict_position', name: '岗位' },
      { dictType: 'dict_user_status', name: '用户状态' },
    ])))
    await p.route('**/dict-data/list**', (route) => fulfill(route, ok([
      { id: '1', label: '办公', value: 'OFFICE', colorType: 'neutral', status: 'ENABLED', sort: 1 },
      { id: '2', label: '直播', value: 'LIVE', colorType: 'success', status: 'ENABLED', sort: 2 },
      { id: '3', label: '拍摄', value: 'SHOOT', colorType: 'warning', status: 'ENABLED', sort: 3 },
    ])))
  })
  await expect(page.getByTestId('dict-type-dict_asset_type')).toBeVisible()
  await expect(page.getByText('OFFICE')).toBeVisible()
  await expect(page.getByText('LIVE')).toBeVisible()
  await expect(page.getByText('SHOOT')).toBeVisible()
})

test('E2E-B2-D-02 类型与值校验', async ({ page }) => {
  await boot(page, '/ims/system/dict', ALL_PERMS, async (p) => {
    await p.route('**/dict-type/list**', (route) => fulfill(route, ok([{ dictType: 'dict_tc_type', name: '测试类型' }])))
    await p.route('**/dict-data/list**', (route) => fulfill(route, ok([])))
    await p.route('**/dict-type/create**', (route) => fulfill(route, ok({})))
    await p.route('**/dict-data/create**', (route) => fulfill(route, ok({})))
  })
  await page.getByTestId('field-dict-type').fill('TC-Type')
  await page.getByTestId('btn-dict-type').click()
  await expect(page.getByTestId('dict-error')).toContainText('格式错误')
  await page.getByTestId('field-dict-type').fill('dict_tc_type')
  await page.getByTestId('field-dict-type-name').fill('测试类型')
  await page.getByTestId('btn-dict-type').click()
  await page.getByTestId('field-dict-value').fill('abc')
  await page.getByTestId('btn-dict-value').click()
  await expect(page.getByTestId('dict-error')).toContainText('字典值格式错误')
  await page.getByTestId('field-dict-value').fill('TC_VALUE_A')
  await page.getByTestId('field-dict-label').fill('测试值A')
  await page.getByTestId('btn-dict-value').click()
  await expect(page.getByText('保存成功')).toBeVisible()
})

test('E2E-B2-D-03 停用值无删除按钮', async ({ page }) => {
  await boot(page, '/ims/system/dict', ALL_PERMS, async (p) => {
    await p.route('**/dict-type/list**', (route) => fulfill(route, ok([{ dictType: 'dict_platform_type', name: '平台' }])))
    await p.route('**/dict-data/list**', (route) => fulfill(route, ok([
      { id: '9', label: '测试值A', value: 'TC_VALUE_A', colorType: 'success', status: 'DISABLED', sort: 1 },
    ])))
  })
  await expect(page.getByTestId('btn-dict-disable')).toHaveCount(0)
  await expect(page.locator('tbody').getByText('停用', { exact: true })).toBeVisible()
})

test('E2E-B2-D-04 内置值标签可辨认', async ({ page }) => {
  await boot(page, '/ims/system/dict', ALL_PERMS, async (p) => {
    await p.route('**/dict-type/list**', (route) => fulfill(route, ok([{ dictType: 'dict_user_status', name: '用户状态' }])))
    await p.route('**/dict-data/list**', (route) => fulfill(route, ok([
      { id: '1', label: '在职', value: 'ACTIVE', colorType: 'success', status: 'ENABLED', sort: 1, builtin: true },
    ])))
  })
  await page.getByTestId('dict-type-dict_user_status').click()
  await expect(page.getByText('在职')).toBeVisible()
  await expect(page.getByText('ACTIVE')).toBeVisible()
})

test('E2E-B2-P-01 参数分组无培训 AI', async ({ page }) => {
  await boot(page, '/ims/system/param', ALL_PERMS, async (p) => {
    await p.route('**/param/list**', (route) => fulfill(route, ok([
      { name: '任务确认自动生成', paramKey: 'work.task.confirm.auto-ai-generate', valueType: 'BOOLEAN', value: 'false', defaultValue: 'false', remark: '' },
    ])))
  })
  for (const name of ['内容审核', '钉钉', '钉钉考勤', 'AI', '通用']) {
    await expect(page.getByTestId(`param-group-${name}`)).toBeVisible()
  }
  await expect(page.getByTestId('training-flag')).toHaveCount(0)
  await expect(page.getByText('新建')).toHaveCount(0)
})

test('E2E-B2-P-02 修改参数', async ({ page }) => {
  await boot(page, '/ims/system/param', ALL_PERMS, async (p) => {
    await p.route('**/param/list**', (route) => fulfill(route, ok([
      { name: '自动生成', paramKey: 'work.task.confirm.auto-ai-generate', valueType: 'BOOLEAN', value: 'false', defaultValue: 'false', remark: '' },
    ])))
    await p.route('**/param/update**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('param-value-work.task.confirm.auto-ai-generate').fill('true')
  await page.getByTestId('btn-param-save').click()
  await expect(page.getByText('参数已更新')).toBeVisible()
})

test('E2E-B2-P-03 钉钉考勤 SECRET 脱敏', async ({ page }) => {
  await boot(page, '/ims/system/param', ALL_PERMS, async (p) => {
    await p.route('**/param/list**', (route) => fulfill(route, ok([
      { name: 'AppSecret', paramKey: 'dingtalk_attendance.app_secret', valueType: 'SECRET', value: 'secret', defaultValue: '', remark: '' },
    ])))
  })
  await page.getByTestId('param-group-钉钉考勤').click()
  await expect(page.getByText('******')).toBeVisible()
})

test('E2E-B2-L-01 操作日志与详情', async ({ page }) => {
  await boot(page, '/ims/system/log', ALL_PERMS, async (p) => {
    await p.route('**/operate-log/page**', (route) => fulfill(route, ok({
      list: [{ id: '1', createTime: '2026-10-13 10:00:00', operatorName: '测试管理员', module: '用户', operation: '编辑用户', result: '成功', ip: '127.0.0.1' }],
      total: 1,
    })))
    await p.route('**/operate-log/get**', (route) => fulfill(route, ok({ requestMethod: 'PUT', requestPath: '/admin-api/ims/system/user/update' })))
  })
  await expect(page.getByText('编辑用户')).toBeVisible()
  await expect(page.getByText('/admin-api/ims/system/user/update')).toHaveCount(0)
  await page.getByTestId('btn-log-detail').click()
  await expect(page.getByTestId('log-detail')).toContainText('PUT')
  await expect(page.getByTestId('log-detail')).toContainText('/admin-api/ims/system/user/update')
})

test('E2E-B2-L-02 登录日志与导出', async ({ page }) => {
  await boot(page, '/ims/system/log', ALL_PERMS, async (p) => {
    await p.route('**/login-log/page**', (route) => fulfill(route, ok({
      list: [{ id: '2', createTime: '2026-10-13 10:01:00', username: 'e2e_u1', loginMethod: '账号密码', result: '密码错', ip: '127.0.0.1' }],
      total: 1,
    })))
    await p.route('**/login-log/export**', (route) => fulfill(route, ok({ taskId: 'log-exp' })))
  })
  await page.getByTestId('tab-login').click()
  await page.getByTestId('login-result').fill('密码错')
  await page.getByTestId('btn-log-query').click()
  await expect(page.getByText('密码错')).toBeVisible()
  await page.getByTestId('btn-log-export').click()
  await expect(page.getByText('登录日志.csv')).toBeVisible()
})

test('E2E-B2-N-01 失败行可补发', async ({ page }) => {
  await boot(page, '/ims/system/notify', ALL_PERMS, async (p) => {
    await p.route('**/notify-record/page**', (route) => {
      const url = new URL(route.request().url())
      const status = url.searchParams.get('status')
      if (status === 'SKIPPED') {
        return fulfill(route, ok({ list: [{ id: '2', eventText: '待办提醒', status: 'SKIPPED', statusText: '去重跳过', bizKey: 'k2', receiverName: '甲', channelText: '站内', createTime: '2026-10-13' }], total: 1 }))
      }
      return fulfill(route, ok({ list: [{ id: '1', eventText: '待办提醒', status: 'FAILED', statusText: '失败', bizKey: 'k1', receiverName: '甲', channelText: '钉钉', createTime: '2026-10-13' }], total: 1 }))
    })
    await p.route('**/notify-record/resend**', (route) => fulfill(route, ok(null)))
  })
  await expect(page.getByText('待办提醒')).toBeVisible()
  await page.getByTestId('btn-resend').click()
  await expect(page.getByText('已补发')).toBeVisible()
  await page.getByTestId('notify-status').selectOption('SKIPPED')
  await expect(page.getByTestId('btn-resend')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '补发通知' })).toHaveCount(0)
})

test('E2E-B2-T-01 套餐维护', async ({ page }) => {
  await boot(page, '/ims/system/tenant', ALL_PERMS, async (p) => {
    await p.route('**/tenant/page**', (route) => fulfill(route, ok({ list: [], total: 0 })))
    await p.route('**/tenant-package/list**', (route) => fulfill(route, ok([{ id: 'p1', name: '测试只读包', menuCount: 1, tenantCount: 0, statusText: '启用' }])))
    await p.route('**/tenant-package/create**', (route) => fulfill(route, ok({ id: 'p1' })))
  })
  await page.getByTestId('tab-package').click()
  await page.getByTestId('btn-package-create').click()
  await expect(page.getByText('套餐已创建')).toBeVisible()
  await expect(page.getByText('测试只读包')).toBeVisible()
})

test('E2E-B2-T-02 新建租户显示一次性密码', async ({ page }) => {
  await boot(page, '/ims/system/tenant', ALL_PERMS, async (p) => {
    await p.route('**/tenant/page**', (route) => fulfill(route, ok({ list: [{ id: '2', name: '测试租户B', packageName: '测试只读包', contactName: '联系人', expireTime: '2027-10-13', status: 'ENABLED' }], total: 1 })))
    await p.route('**/tenant-package/list**', (route) => fulfill(route, ok([])))
    await p.route('**/tenant/create**', (route) => fulfill(route, ok({ tempPassword: 'Init1234ab' })))
  })
  await page.getByTestId('field-tenant-name').fill('测试租户B')
  await page.getByTestId('field-tenant-contact').fill('联系人')
  await page.getByTestId('field-tenant-mobile').fill('13800002222')
  await page.getByTestId('field-tenant-package').fill('测试只读包')
  await page.getByTestId('field-tenant-expire').fill('2027-10-13')
  await page.getByTestId('field-tenant-admin').fill('e2e_tb_admin')
  await page.getByTestId('btn-tenant-create').click()
  await expect(page.getByTestId('tenant-temp-password')).toHaveText('Init1234ab')
})

test('E2E-B2-T-03 分配套餐与停用', async ({ page }) => {
  await boot(page, '/ims/system/tenant', ALL_PERMS, async (p) => {
    await p.route('**/tenant/page**', (route) => fulfill(route, ok({ list: [{ id: '2', name: '测试租户B', packageName: '测试只读包', status: 'ENABLED' }], total: 1 })))
    await p.route('**/tenant-package/list**', (route) => fulfill(route, ok([])))
    await p.route('**/system/tenant/2**', (route) => fulfill(route, ok(null)))
  })
  await page.getByTestId('btn-assign-package').click()
  await expect(page.getByText('套餐已分配')).toBeVisible()
  await page.getByTestId('btn-tenant-disable').click()
  await expect(page.getByText('租户已停用')).toBeVisible()
})

test('E2E-B2-T-04 非平台租户侧栏无租户套餐', async ({ page }) => {
  await boot(page, '/ims/system/user', ['ims:system:user:query'], async (p) => {
    await p.route('**/dept/tree**', (route) => fulfill(route, ok([])))
    await p.route('**/user/page**', (route) => fulfill(route, ok({ list: [], total: 0 })))
  })
  await expect(page.getByText('租户套餐')).toHaveCount(0)
  await expect(page.getByText('菜单')).toHaveCount(0)
})

test('E2E-B2-PC-01 基本信息与修改密码', async ({ page }) => {
  await boot(page, '/profile', [], async (p) => {
    await p.route('**/auth/password/change**', async (route) => {
      const body = route.request().postDataJSON() as { oldPassword?: string }
      if (body.oldPassword !== 'Test1234') return fulfill(route, fail(1214, '当前密码不正确'))
      return fulfill(route, ok(null))
    })
  })
  await page.goto('/profile')
  await expect(page.getByTestId('profile-mobile')).toContainText('138****5678')
  await page.getByTestId('tab-password').click()
  await page.getByTestId('field-old-password').fill('wrong')
  await page.getByTestId('field-new-password').fill('Test5678')
  await page.getByTestId('field-confirm-password').fill('Test5678')
  await page.getByTestId('btn-save-password').click()
  await expect(page.getByTestId('password-error')).toContainText('当前密码不正确')
  await page.getByTestId('field-old-password').fill('Test1234')
  await page.getByTestId('btn-save-password').click()
  await expect(page.getByText('密码已修改')).toBeVisible()
})

test('E2E-B2-PC-02 钉钉用户设置密码', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('ims_access_token', 'access-b2')
    localStorage.setItem('ims_refresh_token', 'refresh-b2')
  })
  await page.route('**/admin-api/ims/**', async (route) => {
    const url = route.request().url()
    if (url.includes('/auth/me')) {
      await fulfill(route, ok({
        user: { id: '7', username: 'ding_a', nickname: '钉钉甲', mainDeptName: '市场一部', deptNames: ['市场一部'], pwdResetRequired: false, mobileMasked: '138****9999', hasPassword: false },
        menus: [],
        permCodes: [],
        permDetails: {},
        dataScopeText: '本部门',
      }))
      return
    }
    if (url.includes('/password/set')) return fulfill(route, ok(null))
    if (url.includes('/session/my')) return fulfill(route, ok({ list: [] }))
    await fulfill(route, ok({}))
  })
  await page.goto('/profile')
  await expect(page.getByTestId('tab-password')).toHaveText('设置密码')
  await expect(page.getByTestId('field-old-password')).toHaveCount(0)
  await page.getByTestId('tab-password').click()
  await page.getByTestId('field-new-password').fill('Test5678')
  await page.getByTestId('btn-save-password').click()
  await expect(page.getByText('密码已设置')).toBeVisible()
})

test('E2E-B2-PC-03 我的会话下线其他设备', async ({ page }) => {
  await boot(page, '/profile', [], async (p) => {
    await p.route('**/session/my**', async (route) => {
      if (route.request().method() === 'DELETE') return fulfill(route, ok(null))
      return fulfill(route, ok({
        list: [
          { sid: 'a', loginTime: '2026-10-13 09:00', ip: '10.0.0.1', current: true },
          { sid: 'b', loginTime: '2026-10-13 09:05', ip: '10.0.0.2', current: false },
        ],
      }))
    })
  })
  await page.goto('/profile')
  await page.getByTestId('tab-sessions').click()
  await expect(page.getByTestId('session-row')).toHaveCount(2)
  await expect(page.getByText('当前')).toBeVisible()
  await page.getByTestId('btn-session-kick').click()
  await expect(page.getByText('已下线')).toBeVisible()
})

test('E2E-B2-BG-01 头像菜单进入个人中心', async ({ page }) => {
  await boot(page, '/ims/system/user', ALL_PERMS, async (p) => {
    await p.route('**/dept/tree**', (route) => fulfill(route, ok([])))
  })
  await page.locator('.user-dropdown').click()
  await page.getByText('个人中心').click()
  await expect(page).toHaveURL(/\/profile$/)
  await expect(page.getByTestId('page-profile')).toBeVisible()
})
