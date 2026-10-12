/**
 * API Mock 数据和处理器
 * 依据: B0a OpenAPI 契约 (ims-backend/openapi.json)
 * 用于 Playwright 测试的 page.route() mock
 */
import type { Page, Route } from '@playwright/test'

// ===== 通用响应结构 =====
export interface CommonResult<T = unknown> {
  code: number
  msg: string
  data: T | null
}

function success<T>(data: T): CommonResult<T> {
  return { code: 0, msg: '成功', data }
}

function error(code: number, msg: string): CommonResult<null> {
  return { code, msg, data: null }
}

// ===== 错误码常量 =====
export const ErrorCode = {
  SUCCESS: 0,
  VALIDATION_FAILED: 1001,
  TOKEN_EXPIRED: 1002,
  NO_PERMISSION: 1008,
  RESOURCE_NOT_FOUND: 1504,
  HAS_CHILDREN: 1502,
  SYSTEM_ERROR: 5007,
}

// ===== Mock 数据 =====

// 登录响应
export const mockLoginResponse = {
  accessToken: 'mock_access_token_123456',
  refreshToken: 'mock_refresh_token_789012',
  expiresIn: 7200,
  pwdResetRequired: false,
}

// 用户信息
export const mockUserInfo = {
  id: '1',
  username: 'admin',
  nickname: '管理员',
  mobile: '138****8888',
  avatar: null,
  status: 'ACTIVE',
  depts: [
    { id: '1', name: '总公司', isMain: true },
    { id: '2', name: '技术部', isMain: false },
  ],
  mainDeptId: '1',
}

// /me 响应
export const mockMeResponse = {
  user: mockUserInfo,
  menus: [
    {
      id: '1',
      name: '首页',
      path: '/dashboard',
      icon: 'home',
      type: 'MENU',
      component: 'Dashboard',
      parentId: null,
      sort: 0,
      visible: true,
      permCode: null,
      children: [],
    },
    {
      id: '2',
      name: '人员管理',
      path: '/user',
      icon: 'user',
      type: 'MENU',
      component: 'UserList',
      parentId: null,
      sort: 1,
      visible: true,
      permCode: 'system:user:list',
      children: [],
    },
    {
      id: '3',
      name: '部门管理',
      path: '/dept',
      icon: 'office-building',
      type: 'MENU',
      component: 'DeptList',
      parentId: null,
      sort: 2,
      visible: true,
      permCode: 'system:dept:list',
      children: [],
    },
  ],
  permCodes: [
    'system:user:list',
    'system:user:create',
    'system:user:update',
    'system:user:delete',
    'system:dept:list',
    'system:dept:create',
    'system:dept:update',
    'system:dept:delete',
  ],
  permDetails: {
    'system:user': { r: true, w: true, d: true },
    'system:dept': { r: true, w: true, d: true },
  },
  dataScopeText: '全部数据',
}

// 只读用户的 /me 响应
export const mockReadOnlyMeResponse = {
  ...mockMeResponse,
  permCodes: ['system:user:list', 'system:dept:list'],
  permDetails: {
    'system:user': { r: true, w: false, d: false },
    'system:dept': { r: true, w: false, d: false },
  },
}

// 无权限用户的 /me 响应
export const mockNoPermMeResponse = {
  ...mockMeResponse,
  menus: [],
  permCodes: [],
  permDetails: {},
  dataScopeText: '暂无权限',
}

// 部门树
export const mockDeptTree = [
  {
    id: '0',
    name: '全部',
    parentId: null,
    source: 'SYSTEM',
    status: 'ENABLED',
    memberCount: 150,
    directMemberCount: 0,
    localOrphan: false,
    leaderName: null,
    children: [
      {
        id: '1',
        name: '总公司',
        parentId: '0',
        source: 'LOCAL',
        status: 'ENABLED',
        memberCount: 100,
        directMemberCount: 10,
        localOrphan: false,
        leaderName: '张三',
        children: [
          {
            id: '2',
            name: '技术部',
            parentId: '1',
            source: 'LOCAL',
            status: 'ENABLED',
            memberCount: 50,
            directMemberCount: 50,
            localOrphan: false,
            leaderName: '李四',
            children: [],
          },
          {
            id: '3',
            name: '运营部',
            parentId: '1',
            source: 'DINGTALK',
            status: 'ENABLED',
            memberCount: 40,
            directMemberCount: 40,
            localOrphan: false,
            leaderName: '王五',
            children: [],
          },
          {
            id: '4',
            name: '市场部(停用)',
            parentId: '1',
            source: 'LOCAL',
            status: 'DISABLED',
            memberCount: 0,
            directMemberCount: 0,
            localOrphan: false,
            leaderName: null,
            children: [],
          },
          {
            id: '5',
            name: '待确认部门',
            parentId: '1',
            source: 'DINGTALK',
            status: 'ENABLED',
            memberCount: 5,
            directMemberCount: 5,
            localOrphan: true,
            leaderName: null,
            children: [],
          },
        ],
      },
      {
        id: '-1',
        name: '待分配',
        parentId: '0',
        source: 'SYSTEM',
        status: 'ENABLED',
        memberCount: 10,
        directMemberCount: 10,
        localOrphan: false,
        leaderName: null,
        children: [],
      },
    ],
  },
]

// 字典数据
export const mockDictData: Record<string, Array<{ value: string; label: string; colorType: string }>> = {
  user_status: [
    { value: 'ACTIVE', label: '在职', colorType: 'success' },
    { value: 'FROZEN', label: '冻结', colorType: 'warning' },
    { value: 'RESIGNED', label: '离职', colorType: 'info' },
  ],
  dept_status: [
    { value: 'ENABLED', label: '启用', colorType: 'success' },
    { value: 'DISABLED', label: '停用', colorType: 'info' },
  ],
  source_type: [
    { value: 'LOCAL', label: '本地', colorType: 'primary' },
    { value: 'DINGTALK', label: '钉钉', colorType: 'warning' },
  ],
}

// 用户列表
export const mockUserList = {
  list: [
    {
      id: '1',
      username: 'zhangsan',
      nickname: '张三',
      mobile: '138****1234',
      status: 'ACTIVE',
      mainDeptName: '技术部',
      source: 'LOCAL',
      createTime: '2024-01-01 10:00:00',
    },
    {
      id: '2',
      username: 'lisi',
      nickname: '李四',
      mobile: '139****5678',
      status: 'FROZEN',
      mainDeptName: '运营部',
      source: 'DINGTALK',
      createTime: '2024-01-02 10:00:00',
    },
    {
      id: '3',
      username: 'wangwu',
      nickname: '王五',
      mobile: '137****9012',
      status: 'RESIGNED',
      mainDeptName: '待分配',
      source: 'LOCAL',
      createTime: '2024-01-03 10:00:00',
    },
  ],
  total: 3,
  pageNo: 1,
  pageSize: 10,
}

// 角色列表
export const mockRoleList = [
  { id: '1', name: '系统管理员', source: 'LOCAL' },
  { id: '2', name: '部门主管', source: 'LOCAL' },
  { id: '3', name: '普通员工', source: 'DINGTALK' },
  { id: '4', name: '只读用户', source: 'LOCAL' },
]

// 组织同步批次
export const mockOrgSyncBatch = {
  batchId: 'batch_001',
  status: 'COMPLETED',
  startedAt: '2024-10-12 08:00:00',
  completedAt: '2024-10-12 08:05:00',
  addedDepts: 2,
  updatedDepts: 5,
  removedDepts: 1,
  addedUsers: 10,
  updatedUsers: 30,
  removedUsers: 5,
  errorMsg: null,
}

// ===== Mock 路由设置函数 =====

/**
 * 设置所有 API mock
 * 只拦截 /admin-api/ 开头的请求，不影响页面加载
 */
export async function setupApiMocks(page: Page, options?: {
  userType?: 'admin' | 'readonly' | 'noperm'
  tokenExpired?: boolean
  networkError?: boolean
}) {
  const { userType = 'admin', tokenExpired = false, networkError = false } = options || {}

  // 网络错误模式 - 只对 API 请求
  if (networkError) {
    await page.route('**/admin-api/**', (route) => {
      route.abort('failed')
    })
    return
  }

  // 登录
  await page.route('**/admin-api/ims/auth/login', async (route) => {
    const request = route.request()
    if (request.method() === 'POST') {
      const body = request.postDataJSON()
      if (body.username === 'admin' && body.password === 'admin123') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(success(mockLoginResponse)),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(error(1214, '用户名或密码错误')),
        })
      }
    }
  })

  // 登出
  await page.route('**/admin-api/ims/auth/logout', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(null)),
    })
  })

  // 刷新令牌
  await page.route('**/admin-api/ims/auth/refresh-token', async (route) => {
    if (tokenExpired) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify(error(ErrorCode.TOKEN_EXPIRED, '刷新令牌已过期')),
      })
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(success({
          accessToken: 'new_access_token_' + Date.now(),
          refreshToken: 'new_refresh_token_' + Date.now(),
          expiresIn: 7200,
          pwdResetRequired: false,
        })),
      })
    }
  })

  // 获取当前用户信息
  await page.route('**/admin-api/ims/auth/me', async (route) => {
    let meResponse = mockMeResponse
    if (userType === 'readonly') {
      meResponse = mockReadOnlyMeResponse
    } else if (userType === 'noperm') {
      meResponse = mockNoPermMeResponse
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(meResponse)),
    })
  })

  // 部门树
  await page.route('**/admin-api/ims/system/dept/tree**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(mockDeptTree)),
    })
  })

  // 部门创建
  await page.route('**/admin-api/ims/system/dept/create', async (route) => {
    const body = route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        id: 'new_dept_' + Date.now(),
        name: body.name,
        parentId: body.parentId,
        source: 'LOCAL',
        status: 'ENABLED',
        sort: body.sort || 0,
        syncOverrideHint: false,
        leaderUserId: body.leaderUserId || null,
      })),
    })
  })

  // 部门更新
  await page.route('**/admin-api/ims/system/dept/update**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        id: '1',
        name: '更新后的部门',
        parentId: '0',
        source: 'LOCAL',
        status: 'ENABLED',
        sort: 0,
        syncOverrideHint: false,
        leaderUserId: null,
      })),
    })
  })

  // 部门删除
  await page.route('**/admin-api/ims/system/dept/delete**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(null)),
    })
  })

  // 部门状态更新
  await page.route('**/admin-api/ims/system/dept/update-status**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(null)),
    })
  })

  // 确认孤立部门
  await page.route('**/admin-api/ims/system/dept/confirm-orphan**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        id: '5',
        name: '待确认部门',
        parentId: '1',
        source: 'DINGTALK',
        status: 'ENABLED',
        sort: 0,
        syncOverrideHint: false,
        leaderUserId: null,
      })),
    })
  })

  // 部门移动
  await page.route('**/admin-api/ims/system/dept/move**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        id: '2',
        name: '技术部',
        parentId: '3',
        source: 'LOCAL',
        status: 'ENABLED',
        sort: 0,
        syncOverrideHint: false,
        leaderUserId: null,
      })),
    })
  })

  // 字典类型列表
  await page.route('**/admin-api/ims/system/dict-type/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success([
        { dictType: 'user_status', name: '用户状态' },
        { dictType: 'dept_status', name: '部门状态' },
        { dictType: 'source_type', name: '来源类型' },
      ])),
    })
  })

  // 字典数据列表
  await page.route('**/admin-api/ims/system/dict-data/simple-list**', async (route) => {
    const url = new URL(route.request().url())
    const dictType = url.searchParams.get('dictType') || url.searchParams.get('dict_type') || ''
    const items = mockDictData[dictType] || []
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(items.map(item => ({
        dictValue: item.value,
        dictLabel: item.label,
        colorType: item.colorType,
        sort: 0,
      })))),
    })
  })

  // 用户分页列表
  await page.route('**/admin-api/ims/system/user/page**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(mockUserList)),
    })
  })

  // 用户简单列表
  await page.route('**/admin-api/ims/system/user/simple-page**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        list: mockUserList.list.map(u => ({
          id: u.id,
          nickname: u.nickname,
          mobile: u.mobile,
          status: u.status,
        })),
        total: mockUserList.total,
        pageNo: 1,
        pageSize: 10,
      })),
    })
  })

  // 用户创建
  await page.route('**/admin-api/ims/system/user/create', async (route) => {
    const body = route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        id: 'new_user_' + Date.now(),
        username: body.username,
        nickname: body.nickname,
        mobile: body.mobile,
        status: 'ACTIVE',
        mainDeptName: '技术部',
        source: 'LOCAL',
        createTime: new Date().toISOString(),
      })),
    })
  })

  // 用户删除
  await page.route('**/admin-api/ims/system/user/delete**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(null)),
    })
  })

  // 用户部门更新
  await page.route('**/admin-api/ims/system/user/update-depts**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(null)),
    })
  })

  // 角色列表
  await page.route('**/admin-api/ims/system/role/simple-list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(mockRoleList)),
    })
  })

  // 组织同步 - 最新批次
  await page.route('**/admin-api/ims/system/org-sync/latest-batch', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success(mockOrgSyncBatch)),
    })
  })

  // 组织同步 - 触发同步
  await page.route('**/admin-api/ims/system/org-sync/reconcile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        ...mockOrgSyncBatch,
        batchId: 'batch_' + Date.now(),
        status: 'RUNNING',
        startedAt: new Date().toISOString(),
        completedAt: null,
      })),
    })
  })

  // 演示错误接口
  await page.route('**/admin-api/ims/demo/error**', async (route) => {
    const url = new URL(route.request().url())
    const code = parseInt(url.searchParams.get('code') || '0')
    
    const errorMessages: Record<number, string> = {
      [ErrorCode.VALIDATION_FAILED]: '字段校验失败',
      [ErrorCode.TOKEN_EXPIRED]: '令牌已过期',
      [ErrorCode.NO_PERMISSION]: '暂无权限',
      [ErrorCode.RESOURCE_NOT_FOUND]: '资源不可用',
      [ErrorCode.HAS_CHILDREN]: '存在关联数据，无法删除',
      [ErrorCode.SYSTEM_ERROR]: '系统繁忙，请稍后再试',
    }

    if (code === 0) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(success({ message: '操作成功' })),
      })
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(error(code, errorMessages[code] || '未知错误')),
      })
    }
  })

  // 健康检查
  await page.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        status: 'healthy',
        version: '1.0.0',
        db: 'ok',
        redis: 'ok',
        football_live: 'ok',
      })),
    })
  })
}

/**
 * 设置特定错误码的 mock
 */
export async function setupErrorMock(page: Page, endpoint: string, code: number, msg: string) {
  await page.route(`**${endpoint}**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(error(code, msg)),
    })
  })
}

/**
 * 设置令牌过期 mock (用于测试令牌刷新流程)
 */
export async function setupTokenExpiredMock(page: Page) {
  let isRefreshed = false

  // 任意 API 请求首次返回 1002，触发刷新流程
  await page.route('**/admin-api/**', async (route) => {
    const url = route.request().url()
    
    // 刷新令牌请求
    if (url.includes('/auth/refresh-token')) {
      isRefreshed = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(success({
          accessToken: 'new_access_token_' + Date.now(),
          refreshToken: 'new_refresh_token_' + Date.now(),
          expiresIn: 7200,
          pwdResetRequired: false,
        })),
      })
      return
    }

    // 登录请求不需要 token
    if (url.includes('/auth/login') || url.includes('/auth/logout')) {
      await route.continue()
      return
    }

    // 第一次请求返回 token 过期
    if (!isRefreshed) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(error(ErrorCode.TOKEN_EXPIRED, '令牌已过期')),
      })
    } else {
      // 刷新后的请求正常返回
      await route.continue()
    }
  })
}

/**
 * 设置并发令牌刷新测试 mock
 */
export async function setupConcurrentRefreshMock(page: Page) {
  let refreshCount = 0
  let isRefreshing = false

  await page.route('**/admin-api/ims/auth/refresh-token', async (route) => {
    refreshCount++
    if (isRefreshing) {
      // 并发刷新请求应该等待第一个刷新完成
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    isRefreshing = true
    
    await new Promise(resolve => setTimeout(resolve, 500)) // 模拟网络延迟
    
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(success({
        accessToken: 'new_access_token_' + Date.now(),
        refreshToken: 'new_refresh_token_' + Date.now(),
        expiresIn: 7200,
        pwdResetRequired: false,
      })),
    })
    
    isRefreshing = false
  })

  return () => refreshCount
}

/**
 * 清除所有 API mock
 */
export async function clearApiMocks(page: Page) {
  await page.unroute('**/admin-api/**')
  await page.unroute('**/health')
}
