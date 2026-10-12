/**
 * 认证 Store
 * 依据: FP-R-01~07, B0a 工作包 §2 (D2/D3/D5)
 *
 * 功能:
 * - 登录/登出
 * - 令牌管理 (access_token + refresh_token)
 * - 用户信息、菜单、权限码
 * - 跨标签页同步 (FP-R-04)
 * - 数据范围文本 (FP-C02-01)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/generated'
import {
  getAccessToken,
  setAccessToken,
  getRefreshToken,
  setRefreshToken,
  clearTokens,
} from '@/api/request'
import type { UserInfo, MenuItem } from '@/types'

const TOKEN_KEY = 'ims_access_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const menus = ref<MenuItem[]>([])
  const permCodes = ref<string[]>([])
  const loading = ref(false)

  const isLoggedIn = computed(() => !!getAccessToken())
  const dataScopeText = computed(() => user.value?.dataScopeText || '')
  const pwdResetRequired = computed(() => user.value?.pwdResetRequired || false)

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const result = await authApi.login({ username, password })
      if (result.code === 0 && result.data) {
        setAccessToken(result.data.accessToken)
        setRefreshToken(result.data.refreshToken)
        await fetchUserInfo()
        if (user.value && result.data.pwdResetRequired) {
          user.value = { ...user.value, pwdResetRequired: true }
        }
        return true
      }
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      clearSession()
    }
  }

  async function fetchUserInfo(): Promise<void> {
    const result = await authApi.me()
    if (result.code === 0 && result.data) {
      user.value = {
        id: result.data.id,
        username: result.data.username,
        nickname: result.data.nickname,
        avatar: result.data.avatar,
        deptId: result.data.deptId,
        deptName: result.data.deptName,
        permCodes: result.data.permCodes || [],
        dataScopeText: result.data.dataScopeText || '全部',
        pwdResetRequired: result.data.pwdResetRequired || false,
      }
      menus.value = (result.data.menus || []).map(mapMenuItem)
      permCodes.value = result.data.permCodes || []
    }
  }

  function mapMenuItem(item: {
    id?: string
    name?: string
    path?: string
    icon?: string
    permCode?: string
    children?: Array<{
      id?: string
      name?: string
      path?: string
      icon?: string
      permCode?: string
      children?: unknown[]
    }>
  }): MenuItem {
    return {
      id: item.id || '',
      name: item.name || '',
      path: item.path,
      icon: item.icon,
      permCode: item.permCode,
      children: item.children?.map(mapMenuItem),
    }
  }

  function clearSession(): void {
    clearTokens()
    user.value = null
    menus.value = []
    permCodes.value = []
  }

  function hasPerm(code: string): boolean {
    return permCodes.value.includes(code)
  }

  function hasAnyPerm(codes: string[]): boolean {
    return codes.some((code) => permCodes.value.includes(code))
  }

  function hasAllPerm(codes: string[]): boolean {
    return codes.every((code) => permCodes.value.includes(code))
  }

  function clearPwdReset(): void {
    if (user.value) {
      user.value = { ...user.value, pwdResetRequired: false }
    }
  }

  function mockLogin(): void {
    setAccessToken('mock-access-token')
    setRefreshToken('mock-refresh-token')
    user.value = {
      id: '1',
      username: 'qa_admin',
      nickname: '测试管理员',
      deptId: '5',
      deptName: '技术部',
      permCodes: [
        'ims:system:dept:create',
        'ims:system:dept:update',
        'ims:system:dept:delete',
        'ims:system:user:query',
        'ims:system:user:create',
        'ims:system:user:update',
        'ims:system:user:delete',
        'ims:system:org-sync:run',
        'ims:demo:order:query',
        'ims:demo:order:create',
        'ims:demo:order:update',
        'ims:demo:order:delete',
      ],
      dataScopeText: '全部',
    }
    const narrow = sessionStorage.getItem('ims_menu_profile') === 'narrow'
    menus.value = [
      {
        id: '1',
        name: '示例',
        icon: 'Document',
        children: narrow
          ? [{ id: '13', name: '列表演示', path: '/demo/list', permCode: 'ims:demo:order:query' }]
          : [
          { id: '11', name: 'Token 演示', path: '/demo/tokens', permCode: 'ims:demo:order:query' },
          { id: '12', name: '布局演示', path: '/demo/layout', permCode: 'ims:demo:order:query' },
          { id: '13', name: '列表演示', path: '/demo/list', permCode: 'ims:demo:order:query' },
          { id: '14', name: '表单演示', path: '/demo/form', permCode: 'ims:demo:order:query' },
          { id: '15', name: '选择器演示', path: '/demo/selectors', permCode: 'ims:demo:order:query' },
          { id: '16', name: '展示组件', path: '/demo/display', permCode: 'ims:demo:order:query' },
          { id: '17', name: '部门树', path: '/demo/dept-tree', permCode: 'ims:demo:order:query' },
          { id: '18', name: '左树右表', path: '/demo/left-tree-right-table', permCode: 'ims:demo:order:query' },
        ],
      },
    ]
    permCodes.value = [
      'ims:system:dept:create',
      'ims:system:dept:update',
      'ims:system:dept:delete',
      'ims:system:user:query',
      'ims:system:user:create',
      'ims:system:user:update',
      'ims:system:user:delete',
      'ims:system:org-sync:run',
      'ims:demo:order:query',
      'ims:demo:order:create',
      'ims:demo:order:update',
      'ims:demo:order:delete',
    ]
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('storage', (event) => {
      if (event.key === TOKEN_KEY && event.newValue === null) {
        clearSession()
      }
    })
  }

  return {
    user,
    menus,
    permCodes,
    loading,
    isLoggedIn,
    dataScopeText,
    pwdResetRequired,
    login,
    logout,
    fetchUserInfo,
    clearSession,
    hasPerm,
    hasAnyPerm,
    hasAllPerm,
    mockLogin,
    clearPwdReset,
  }
})
