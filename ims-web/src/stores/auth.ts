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
import { changePassword as changePasswordApi } from '@/api/password'
import {
  ApiError,
  getAccessToken,
  setAccessToken,
  setRefreshToken,
  clearTokens,
} from '@/api/request'
import type { components } from '@/api/generated/api-types'
import type { UserInfo, MenuItem } from '@/types'

type MeData = components['schemas']['MeResponse']
type MeMenu = components['schemas']['MenuItem']

const PWD_RESET_KEY = 'ims_pwd_reset'
const LOGIN_METHOD_KEY = 'ims_last_login_method'

export interface LoginFailure {
  ok: false
  code: number
  msg: string
  data: unknown
}

export interface LoginSuccess {
  ok: true
  pwdResetRequired: boolean
}

const TOKEN_KEY = 'ims_access_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const menus = ref<MenuItem[]>([])
  const permCodes = ref<string[]>([])
  const loading = ref(false)

  const tokenVersion = ref(0)
  const isLoggedIn = computed(() => tokenVersion.value >= 0 && !!getAccessToken())
  const dataScopeText = computed(() => user.value?.dataScopeText || '')
  const pwdResetRequired = computed(() => user.value?.pwdResetRequired || false)

  async function login(username: string, password: string): Promise<LoginSuccess | LoginFailure> {
    loading.value = true
    try {
      const result = await authApi.login(
        { username: username.trim(), password },
        { skipGlobalError: true },
      )
      if (result.code === 0 && result.data) {
        setAccessToken(result.data.accessToken)
        setRefreshToken(result.data.refreshToken)
        tokenVersion.value += 1
        const reset = Boolean(result.data.pwdResetRequired)
        if (reset) sessionStorage.setItem(PWD_RESET_KEY, '1')
        else sessionStorage.removeItem(PWD_RESET_KEY)
        try {
          await fetchUserInfo()
        } catch {
          // 令牌已签发。/me 失败不撤销本次登录，页面仍按 pwdResetRequired 跳转。
        }
        if (reset && user.value) {
          user.value = { ...user.value, pwdResetRequired: true }
        }
        localStorage.setItem(LOGIN_METHOD_KEY, 'password')
        return { ok: true, pwdResetRequired: reset || Boolean(user.value?.pwdResetRequired) }
      }
      return { ok: false, code: result.code, msg: result.msg, data: result.data }
    } catch (err) {
      if (err instanceof ApiError) {
        return { ok: false, code: err.code, msg: err.message, data: err.data }
      }
      return { ok: false, code: -1, msg: '网络异常，请检查网络后重试', data: null }
    } finally {
      loading.value = false
    }
  }

  /**
   * 提交改密。仅在接口 code=0 后清除强制改密标记。
   * 改密接口尚未进入 B0a generated client，走 api/password.ts 适配层。
   */
  async function submitPasswordChange(oldPassword: string, newPassword: string): Promise<LoginSuccess | LoginFailure> {
    try {
      await changePasswordApi({ oldPassword, newPassword })
      sessionStorage.removeItem(PWD_RESET_KEY)
      try {
        await fetchUserInfo()
      } catch {
        // 改密已成功时仍允许离开本页；/me 失败由后续请求的 1002 处理。
      }
      if (user.value?.pwdResetRequired) {
        sessionStorage.setItem(PWD_RESET_KEY, '1')
      } else if (user.value) {
        user.value = { ...user.value, pwdResetRequired: false }
      }
      return { ok: true, pwdResetRequired: Boolean(user.value?.pwdResetRequired) }
    } catch (err) {
      if (err instanceof ApiError) {
        return { ok: false, code: err.code, msg: err.message, data: err.data }
      }
      return { ok: false, code: -1, msg: '网络异常，请检查网络后重试', data: null }
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
      applyMe(result.data)
    }
  }

  /** 按 B0a MeResponse 读取：id 保持字符串，不转成 number。 */
  function applyMe(data: MeData): void {
    const profile = data.user
    const extra = profile as typeof profile & {
      mobileMasked?: string | null
      roleNames?: string[]
      hasPassword?: boolean
      positionLabel?: string | null
    }
    user.value = {
      id: String(profile.id),
      username: profile.username,
      nickname: profile.nickname,
      avatar: profile.avatar || undefined,
      // B0a MeResponse.user 只有 deptNames / mainDeptName，没有 deptId。
      // 部门 id 等 B2 用户接口再补，这里不能把部门名称写进 id。
      deptId: '',
      deptName: profile.mainDeptName || profile.deptNames?.[0] || '',
      permCodes: data.permCodes || [],
      dataScopeText: data.dataScopeText || '',
      pwdResetRequired: Boolean(profile.pwdResetRequired),
      mobileMasked: extra.mobileMasked ?? null,
      roleNames: extra.roleNames || [],
      hasPassword: extra.hasPassword !== false,
      positionLabel: extra.positionLabel ?? null,
    }
    menus.value = (data.menus || []).map(mapMenuItem)
    permCodes.value = data.permCodes || []
  }

  function mapMenuItem(item: MeMenu): MenuItem {
    return {
      id: item.id || '',
      name: item.name || '',
      path: item.path || undefined,
      icon: item.icon || undefined,
      permCode: item.permCode || undefined,
      type: item.type || undefined,
      children: item.children?.map(mapMenuItem) || [],
    }
  }

  /** 钉钉落地页写入令牌后，让登录态和跨标签页监听生效。 */
  function adoptSession(): void {
    tokenVersion.value += 1
    localStorage.setItem(LOGIN_METHOD_KEY, 'dingtalk')
  }

  function clearSession(): void {
    clearTokens()
    tokenVersion.value += 1
    user.value = null
    menus.value = []
    permCodes.value = []
    sessionStorage.removeItem(PWD_RESET_KEY)
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
    sessionStorage.removeItem(PWD_RESET_KEY)
    if (user.value) {
      user.value = { ...user.value, pwdResetRequired: false }
    }
  }

  function mockLogin(): void {
    setAccessToken('mock-access-token')
    setRefreshToken('mock-refresh-token')
    tokenVersion.value += 1
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
    submitPasswordChange,
    adoptSession,
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
