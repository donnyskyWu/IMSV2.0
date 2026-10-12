/**
 * 认证 Store
 * 依据: FP-R-04 会话 Store
 * 注意: 本步只做骨架，真实接口接入等 B0a 契约冻结后再做
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, MenuItem } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'))
  const user = ref<UserInfo | null>(null)
  const menus = ref<MenuItem[]>([])
  const permCodes = ref<string[]>([])

  // 计算属性
  const isLoggedIn = computed(() => !!accessToken.value)
  const dataScopeText = computed(() => user.value?.dataScopeText || '')
  const pwdResetRequired = computed(() => user.value?.pwdResetRequired || false)

  // 设置 Token
  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
  }

  // 清除会话
  function clearSession() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    menus.value = []
    permCodes.value = []
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  // 设置用户信息 (模拟，真实接口待 B0a)
  function setUserInfo(info: UserInfo, menuList: MenuItem[], codes: string[]) {
    user.value = info
    menus.value = menuList
    permCodes.value = codes
  }

  // 权限判断
  function hasPerm(code: string): boolean {
    return permCodes.value.includes(code)
  }

  function hasAnyPerm(codes: string[]): boolean {
    return codes.some((code) => permCodes.value.includes(code))
  }

  function hasAllPerm(codes: string[]): boolean {
    return codes.every((code) => permCodes.value.includes(code))
  }

  // 模拟数据 (用于示例页)
  function mockLogin() {
    setTokens('mock-access-token', 'mock-refresh-token')
    setUserInfo(
      {
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
      },
      [
        {
          id: '1',
          name: '示例',
          icon: 'Document',
          children: [
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
      ],
      [
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
    )
  }

  return {
    accessToken,
    refreshToken,
    user,
    menus,
    permCodes,
    isLoggedIn,
    dataScopeText,
    pwdResetRequired,
    setTokens,
    clearSession,
    setUserInfo,
    hasPerm,
    hasAnyPerm,
    hasAllPerm,
    mockLogin,
  }
})
