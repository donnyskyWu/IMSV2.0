/**
 * Vue Router 配置
 * 依据: FP-R-07 路由守卫与动态路由
 * FP-R-09 (§2.2 #9): test 构建提供 /__routes 接口
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { beginAuthNavigation, endAuthNavigation } from '@/utils/auth-navigation'
import {
  isPasswordPath,
  landingPath,
  PASSWORD_RESET_PATH,
  resolveLanding,
  sanitizeRedirect,
} from '@/utils/login-landing'

// 示例页路由 (仅 dev/test 构建注册)
const demoRoutes: RouteRecordRaw[] = [
  {
    path: '/demo/tokens',
    name: 'DemoTokens',
    component: () => import('@/views/demo/TokensDemo.vue'),
    meta: { title: 'Token 演示' },
  },
  {
    path: '/demo/layout',
    name: 'DemoLayout',
    component: () => import('@/views/demo/LayoutDemo.vue'),
    meta: { title: '布局演示' },
  },
  {
    path: '/demo/list',
    name: 'DemoList',
    component: () => import('@/views/demo/ListDemo.vue'),
    meta: { title: '列表演示' },
  },
  {
    path: '/demo/tabs-list',
    name: 'DemoTabsList',
    component: () => import('@/views/demo/TabsListDemo.vue'),
    meta: { title: 'Tab 列表演示' },
  },
  {
    path: '/demo/form',
    name: 'DemoForm',
    component: () => import('@/views/demo/FormDemo.vue'),
    meta: { title: '表单演示' },
  },
  {
    path: '/demo/selectors',
    name: 'DemoSelectors',
    component: () => import('@/views/demo/SelectorsDemo.vue'),
    meta: { title: '选择器演示' },
  },
  {
    path: '/demo/files',
    name: 'DemoFiles',
    component: () => import('@/views/demo/FilesDemo.vue'),
    meta: { title: '文件演示' },
  },
  {
    path: '/demo/display',
    name: 'DemoDisplay',
    component: () => import('@/views/demo/DisplayDemo.vue'),
    meta: { title: '展示组件' },
  },
  {
    path: '/demo/dept-tree',
    name: 'DemoDeptTree',
    component: () => import('@/views/demo/DeptTreeDemo.vue'),
    meta: { title: '部门树' },
  },
  {
    path: '/demo/left-tree-right-table',
    name: 'DemoLeftTreeRightTable',
    component: () => import('@/views/demo/LeftTreeRightTableDemo.vue'),
    meta: { title: '左树右表' },
  },
  {
    path: '/demo/workbench',
    name: 'DemoWorkbench',
    component: () => import('@/views/demo/WorkbenchDemo.vue'),
    meta: { title: '工作台', menuless: true },
  },
  {
    path: '/demo/fill',
    name: 'DemoFill',
    component: () => import('@/views/demo/FillDemo.vue'),
    meta: { title: '填报页', menuless: true },
  },
  {
    path: '/demo/request',
    name: 'DemoRequest',
    component: () => import('@/views/demo/RequestDemo.vue'),
    meta: { title: '请求演示' },
  },
]

// 登录页（生产与开发都保留）
const loginRoute: RouteRecordRaw = {
  path: '/login',
  name: 'Login',
  component: () => import('@/views/Login.vue'),
  meta: { title: '登录', public: true },
}

const changePasswordRoute: RouteRecordRaw = {
  path: PASSWORD_RESET_PATH,
  name: 'ChangePassword',
  component: () => import('@/views/ChangePassword.vue'),
  meta: { title: '请先修改密码', menuless: true },
}

/** B0b 已登记路径，与 /password-reset 同一页面。 */
const changePasswordAliasRoute: RouteRecordRaw = {
  path: '/user/change-password',
  name: 'ChangePasswordAlias',
  component: () => import('@/views/ChangePassword.vue'),
  meta: { title: '请先修改密码', menuless: true },
}

/**
 * B1 已登记业务页。标题以 01 功能点清单为准。
 * 不登记工作台，也不登记 /system/dept 等后续菜单。
 */
/** B5 公司资源。四个叶子挂在公司资产 / 资源管理下。 */
const b5Routes: RouteRecordRaw[] = [
  {
    path: '/ims/corp/resource/company',
    name: 'CorpCompany',
    component: () => import('@/views/corp/CompanyList.vue'),
    meta: { title: '公司管理', perm: 'ims:corp:company:query' },
  },
  {
    path: '/ims/corp/resource/realname',
    name: 'CorpRealname',
    component: () => import('@/views/corp/RealnameList.vue'),
    meta: { title: '实名人管理', perm: 'ims:corp:realname:query' },
  },
  {
    path: '/ims/corp/resource/sim-card',
    name: 'CorpSimCard',
    component: () => import('@/views/corp/SimCardList.vue'),
    meta: { title: '手机卡管理', perm: 'ims:corp:sim:query' },
  },
  {
    path: '/ims/corp/resource/certificate',
    name: 'CorpCertificate',
    component: () => import('@/views/corp/CertificatePage.vue'),
    meta: { title: '证件管理', perm: 'ims:cert:archive:query' },
  },
]

const b1Routes: RouteRecordRaw[] = [
  {
    path: '/ims/auth/org',
    name: 'AuthOrg',
    component: () => import('@/views/auth/OrgSync.vue'),
    meta: { title: '组织架构同步' },
  },
  {
    path: '/ims/auth/position',
    name: 'AuthPosition',
    component: () => import('@/views/auth/PositionRules.vue'),
    meta: { title: '岗位-角色供给规则' },
  },
]

/**
 * B3 个人工作台路由。
 * /ims/workbench 是菜单，/todos 和 /messages 是无菜单子页面。
 */
const b3Routes: RouteRecordRaw[] = [
  {
    path: '/ims/workbench',
    name: 'Workbench',
    component: () => import('@/views/workbench/index.vue'),
    meta: { title: '个人工作台' },
  },
  {
    path: '/ims/workbench/todos',
    name: 'WorkbenchTodos',
    component: () => import('@/views/workbench/todos/index.vue'),
    meta: { title: '待办中心', menuless: true },
  },
  {
    path: '/ims/workbench/messages',
    name: 'WorkbenchMessages',
    component: () => import('@/views/workbench/messages/index.vue'),
    meta: { title: '消息中心', menuless: true },
  },
]

/** 壳路径。无菜单时停在这里，提示由 AppLayout 内容区展示。 */
const shellRoute: RouteRecordRaw = {
  path: '/',
  name: 'AppShell',
  component: () => import('@/views/AppShell.vue'),
  meta: { title: 'IMS', shell: true },
}

/** 未登记的地址走无权限页，不展示业务数据。 */
const unknownRoute: RouteRecordRaw = {
  path: '/:pathMatch(.*)*',
  name: 'UnknownRoute',
  component: () => import('@/views/AppShell.vue'),
  meta: { title: '无权限' },
}

// dev/test 注册示例页；生产构建不注册，/demo/* 回首页（§2.2 #9、§2.3 U4）
const demoEnabled = import.meta.env.DEV || import.meta.env.MODE === 'test'

const routes: RouteRecordRaw[] = demoEnabled
  ? [
      shellRoute,
      loginRoute,
      changePasswordRoute,
      changePasswordAliasRoute,
      ...b1Routes,
      ...b3Routes,
      ...b5Routes,
      ...demoRoutes,
      unknownRoute,
    ]
  : [
      {
        path: '/',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页', public: true, shell: true },
      },
      loginRoute,
      changePasswordRoute,
      changePasswordAliasRoute,
      ...b1Routes,
      ...b3Routes,
      ...b5Routes,
      {
        path: '/demo/:pathMatch(.*)*',
        redirect: '/',
      },
      unknownRoute,
    ]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function registeredRoutePaths(): string[] {
  return router.getRoutes().map((route) => route.path).filter((path) => path && !path.includes(':'))
}

function mustResetPassword(): boolean {
  const authStore = useAuthStore()
  return authStore.pwdResetRequired || sessionStorage.getItem('ims_pwd_reset') === '1'
}

function failureCode(err: unknown): number | undefined {
  if (typeof err === 'object' && err !== null && 'code' in err) {
    const code = (err as { code: unknown }).code
    return typeof code === 'number' ? code : undefined
  }
  return undefined
}

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 生产构建不提供示例页：/demo/* 跳首页，且不经过登录（§2.3 U4）
  if (!demoEnabled && (to.path === '/demo' || to.path.startsWith('/demo/'))) {
    next({ path: '/', replace: true })
    return
  }

  const loggedIn = !!localStorage.getItem('ims_access_token')

  // 已登录再打开登录页：直接进入系统或改密页（FP-B1-LG-01）
  if (to.path === '/login' && loggedIn) {
    beginAuthNavigation()
    try {
      if (!authStore.user) await authStore.fetchUserInfo()
    } catch {
      authStore.clearSession()
      next()
      return
    } finally {
      endAuthNavigation()
    }
    if (mustResetPassword()) {
      const redirect = sanitizeRedirect(to.query.redirect)
      next({ path: PASSWORD_RESET_PATH, query: redirect ? { redirect } : {} })
      return
    }
    next(landingPath({
      redirect: to.query.redirect,
      menus: authStore.menus,
      registeredPaths: registeredRoutePaths(),
    }))
    return
  }

  // 生产首页对未登录仍公开。已登录停在壳路径时继续往下走，以便套布局。
  if (to.meta.public && !(loggedIn && to.meta.shell)) {
    next()
    return
  }

  if (!loggedIn) {
    const requireAuth = sessionStorage.getItem('ims_require_auth') === '1'
    // 开发环境打开 / 仍进示例页，避免壳路径挡住 B0b 演示。
    if (demoEnabled && to.path === '/' && !requireAuth) {
      next('/demo/tokens')
      return
    }
    // 示例页自动登录 (模拟)。VC-R-15 写入 ims_require_auth 后走真实跳转。
    if (demoEnabled && to.path.startsWith('/demo') && !requireAuth) {
      authStore.mockLogin()
      next()
      return
    }
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (mustResetPassword() && !isPasswordPath(to.path)) {
    const redirect = sanitizeRedirect(to.query.redirect) || sanitizeRedirect(to.fullPath)
    next({
      path: PASSWORD_RESET_PATH,
      query: redirect ? { redirect } : {},
    })
    return
  }

  // 刷新后 Pinia 清空，用 /me 恢复权限（只读用户因此看不到写操作）
  if (authStore.permCodes.length === 0 && !isPasswordPath(to.path)) {
    beginAuthNavigation()
    try {
      await authStore.fetchUserInfo()
    } catch (err) {
      const code = failureCode(err)
      // 刷新在请求层里完成。失败后再回登录页，这里不提前清 refresh token。
      if (code === 1002 || code === 1003) {
        sessionStorage.setItem('ims_require_auth', '1')
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
      if (demoEnabled && to.path.startsWith('/demo')) {
        authStore.mockLogin()
      }
    } finally {
      endAuthNavigation()
    }
  }

  if (mustResetPassword() && !isPasswordPath(to.path)) {
    next(PASSWORD_RESET_PATH)
    return
  }

  // 已登录打开壳路径，且菜单里有可落地页面时，按 LG-08 进入该页。
  if (to.meta.shell) {
    const landing = resolveLanding({
      menus: authStore.menus,
      registeredPaths: registeredRoutePaths(),
    })
    if (landing && landing !== to.path) {
      next(landing)
      return
    }
  }

  next()
})

// 设置页面标题
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - IMS` : 'IMS'
})

export default router

/**
 * 获取路由清单 (FP-R-09)
 * 格式: [{path, name, meta}]
 * 仅在 test 构建中使用，用于全局冒烟测试
 */
export function getRoutesList(): Array<{ path: string; name: string; meta: Record<string, unknown> }> {
  return router.getRoutes()
    .filter((route) => {
      // 排除重定向和无名路由
      if (!route.name || route.redirect) return false
      // §2.2 #9: 冒烟只覆盖 /demo/*，登录页归 B1
      if (!route.path.startsWith('/demo')) return false
      return true
    })
    .map((route) => ({
      path: route.path,
      name: String(route.name),
      meta: route.meta as Record<string, unknown>,
    }))
}

// 暴露给全局，供 /__routes 使用 (仅 dev/test 构建)
if (demoEnabled) {
  ;(window as unknown as Record<string, unknown>).__getRoutesList = getRoutesList
}
