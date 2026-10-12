/**
 * Vue Router 配置
 * 依据: FP-R-07 路由守卫与动态路由
 * FP-R-09 (§2.2 #9): test 构建提供 /__routes 接口
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
  path: '/user/change-password',
  name: 'ChangePassword',
  component: () => import('@/views/ChangePassword.vue'),
  meta: { title: '修改密码' },
}

// dev/test 注册示例页；生产构建不注册，/demo/* 回首页（§2.2 #9、§2.3 U4）
const demoEnabled = import.meta.env.DEV || import.meta.env.MODE === 'test'

const routes: RouteRecordRaw[] = demoEnabled
  ? [
      { path: '/', redirect: '/demo/tokens' },
      loginRoute,
      changePasswordRoute,
      ...demoRoutes,
    ]
  : [
      {
        path: '/',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页', public: true },
      },
      loginRoute,
      changePasswordRoute,
      {
        path: '/demo/:pathMatch(.*)*',
        redirect: '/',
      },
    ]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 生产构建不提供示例页：/demo/* 跳首页，且不经过登录（§2.3 U4）
  if (!demoEnabled && (to.path === '/demo' || to.path.startsWith('/demo/'))) {
    next({ path: '/', replace: true })
    return
  }

  // 公开页面
  if (to.meta.public) {
    next()
    return
  }

  // 密码被重置后只能停留在改密页（登录响应可能先于用户信息）
  const mustReset = authStore.pwdResetRequired || sessionStorage.getItem('ims_pwd_reset') === '1'
  if (mustReset && to.path !== '/user/change-password') {
    next('/user/change-password')
    return
  }

  // 未登录 → 跳登录页 (FP-R-07)。令牌在 localStorage，不能用无依赖的 computed。
  const loggedIn = !!localStorage.getItem('ims_access_token')
  if (!loggedIn) {
    const requireAuth = sessionStorage.getItem('ims_require_auth') === '1'
    // 示例页自动登录 (模拟)。VC-R-15 写入 ims_require_auth 后走真实跳转。
    if (demoEnabled && to.path.startsWith('/demo') && !requireAuth) {
      authStore.mockLogin()
      next()
      return
    }
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 刷新后 Pinia 清空，用 /me 恢复权限（只读用户因此看不到写操作）
  if (!to.meta.public && authStore.permCodes.length === 0) {
    try {
      await authStore.fetchUserInfo()
    } catch {
      if (demoEnabled && to.path.startsWith('/demo')) {
        authStore.mockLogin()
      }
    }
  }

  // 需要修改密码 (FP-R-04)
  if (authStore.pwdResetRequired && to.path !== '/user/change-password') {
    next('/user/change-password')
    return
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
