/**
 * Axios 请求层
 * 依据: FP-R-01~07, B0a 工作包 §2 (D2/D3/D5)
 *
 * 功能:
 * - 统一响应格式 CommonResult: { code, msg, data }
 * - 错误码处理 (1001 校验失败、1008 无权限、5xxx 系统异常等)
 * - 令牌管理: access_token + refresh_token
 * - 静默刷新: access_token 过期时自动刷新 (FP-R-03)
 * - 并发刷新: 多个请求同时过期只刷新一次 (FP-R-03)
 * - 跳转登录: refresh_token 也过期时跳转登录页并带 redirect (D3)
 * - 跨标签页同步: localStorage 事件监听 (FP-R-04)
 */
import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { isAuthNavigation } from '@/utils/auth-navigation'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 为 true 时不弹全局 toast，由调用方按错误码展示（登录 / 改密页） */
    skipGlobalError?: boolean
  }
}

/** 业务错误。拦截器拒绝时带上 code 与 data，页面据此展示白名单文案。 */
export class ApiError extends Error {
  code: number
  data: unknown

  constructor(code: number, msg: string, data: unknown = null) {
    super(msg)
    this.name = 'ApiError'
    this.code = code
    this.data = data
  }
}

const TOKEN_KEY = 'ims_access_token'
const REFRESH_TOKEN_KEY = 'ims_refresh_token'
const REDIRECT_KEY = 'ims_redirect_url'

export interface CommonResult<T = unknown> {
  code: number
  msg: string
  data: T | null
}

export const ErrorCode = {
  SUCCESS: 0,
  VALIDATION_FAILED: 1001,
  TOKEN_EXPIRED: 1002,
  KICKED_OFFLINE: 1003,
  NO_PERMISSION: 1008,
  RESOURCE_NOT_FOUND: 1504,
  SYSTEM_ERROR: 5007,
  NETWORK_ERROR: -1,
} as const

let isRefreshing = false
let refreshSubscribers: Array<(token: string | null) => void> = []

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((callback) => callback(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(callback: (token: string | null) => void) {
  refreshSubscribers.push(callback)
}

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

function generateTraceId(): string {
  return Math.random().toString(36).substring(2, 10)
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return null
  }

  try {
    const response = await axios.post<CommonResult<{ accessToken: string; refreshToken: string }>>(
      '/admin-api/ims/auth/refresh-token',
      { refreshToken }
    )

    if (response.data.code === 0 && response.data.data) {
      const { accessToken, refreshToken: newRefreshToken } = response.data.data
      setAccessToken(accessToken)
      setRefreshToken(newRefreshToken)
      return accessToken
    }
    return null
  } catch {
    return null
  }
}

let loginRedirecting = false

function redirectToLogin(message = '登录已失效，请重新登录'): void {
  clearTokens()
  // 记下需要真实登录，避免开发环境在浏览器后退时又自动进入示例页。
  sessionStorage.setItem('ims_require_auth', '1')
  // 同一轮失败只跳一次，排队中的请求不再各跳一次。
  if (loginRedirecting) return
  loginRedirecting = true
  queueMicrotask(() => {
    loginRedirecting = false
  })
  // 守卫还在等 /me 的刷新结果，由守卫带上原路径跳转。
  if (isAuthNavigation()) {
    ElMessage.warning(message)
    return
  }
  const currentPath = router.currentRoute.value.fullPath
  if (currentPath !== '/login' && !currentPath.startsWith('/login?')) {
    localStorage.setItem(REDIRECT_KEY, currentPath)
    router.push({
      path: '/login',
      query: { redirect: currentPath },
    })
    ElMessage.warning(message)
  }
}

function isRefreshCall(config: InternalAxiosRequestConfig): boolean {
  return (config.url || '').includes('/auth/refresh-token')
}

async function handleTokenExpired(
  instance: AxiosInstance,
  originalRequest: InternalAxiosRequestConfig & { _retry?: boolean },
  code: number,
  message: string,
  data: unknown,
) {
  const expiredMessage = '登录已失效，请重新登录'
  // 已经重放过、本身就是刷新接口、或本地没有刷新令牌：不再刷新。
  if (originalRequest._retry || isRefreshCall(originalRequest) || !getRefreshToken()) {
    redirectToLogin(expiredMessage)
    throw new ApiError(code, message, data)
  }
  originalRequest._retry = true

  if (isRefreshing) {
    const token = await new Promise<string | null>((resolve) => {
      addRefreshSubscriber(resolve)
    })
    if (!token) throw new ApiError(code, message, data)
    originalRequest.headers.Authorization = `Bearer ${token}`
    return instance(originalRequest)
  }

  isRefreshing = true
  try {
    const newToken = await refreshAccessToken()
    onRefreshed(newToken)
    if (!newToken) {
      redirectToLogin(expiredMessage)
      throw new ApiError(code, message, data)
    }
    originalRequest.headers.Authorization = `Bearer ${newToken}`
    return instance(originalRequest)
  } finally {
    isRefreshing = false
  }
}

function handleErrorCode(code: number, msg: string): void {
  switch (code) {
    case ErrorCode.VALIDATION_FAILED:
      break

    case ErrorCode.NO_PERMISSION:
      ElMessage.error('暂无权限')
      break

    case ErrorCode.RESOURCE_NOT_FOUND:
      ElMessage.warning('资源不可用')
      break

    case ErrorCode.SYSTEM_ERROR:
    default:
      if (code >= 5000) {
        const traceId = generateTraceId()
        ElMessage.error(`系统繁忙，请稍后再试 问题编号：${traceId}`)
      } else if (msg) {
        ElMessage.error(msg)
      }
      break
  }
}

function createRequest(): AxiosInstance {
  const instance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = getAccessToken()
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  instance.interceptors.response.use(
    (response) => {
      const result = response.data as CommonResult

      if (result.code === ErrorCode.SUCCESS) {
        return response
      }

      if (result.code === ErrorCode.KICKED_OFFLINE) {
        redirectToLogin('您的账号已在其他设备登录，本设备已下线')
        return Promise.reject(new ApiError(result.code, result.msg || 'kicked', result.data))
      }

      if (result.code === ErrorCode.TOKEN_EXPIRED) {
        return handleTokenExpired(
          instance,
          response.config,
          result.code,
          result.msg || '登录已失效，请重新登录',
          result.data,
        )
      }

      // 登录 / 改密自行展示 1214 等文案，避免和全局 toast 重复
      if (!response.config.skipGlobalError) {
        handleErrorCode(result.code, result.msg)
      }
      return Promise.reject(new ApiError(result.code, result.msg || '请求失败', result.data))
    },
    async (error: AxiosError) => {
      // Q8：401 + 1002 有刷新令牌就先静默刷新并重放；1003 直接回登录页。
      // 其它 401 保留后端原始 code，不改写成 1002。
      if (error.response?.status === 401 && error.config) {
        const result = (typeof error.response.data === 'object' && error.response.data)
          ? error.response.data as CommonResult
          : undefined
        const code = typeof result?.code === 'number' ? result.code : undefined
        if (code === ErrorCode.KICKED_OFFLINE) {
          const message = '您的账号已在其他设备登录，本设备已下线'
          redirectToLogin(message)
          return Promise.reject(new ApiError(code, message, result?.data ?? null))
        }
        if (code === ErrorCode.TOKEN_EXPIRED) {
          return handleTokenExpired(
            instance,
            error.config,
            code,
            result?.msg || '登录已失效，请重新登录',
            result?.data ?? null,
          )
        }
        if (code !== undefined) {
          if (!error.config.skipGlobalError) handleErrorCode(code, result?.msg || '')
          return Promise.reject(new ApiError(code, result?.msg || '请求失败', result?.data ?? null))
        }
      }

      const silent = Boolean(error.config?.skipGlobalError)

      if (!error.response) {
        if (!silent) ElMessage.error('网络异常，请检查网络后重试')
        return Promise.reject(new ApiError(ErrorCode.NETWORK_ERROR, '网络异常，请检查网络后重试'))
      }

      const result = error.response?.data as CommonResult | undefined
      if (result?.code) {
        if (!silent) handleErrorCode(result.code, result.msg)
        return Promise.reject(new ApiError(result.code, result.msg || '请求失败', result.data))
      }

      return Promise.reject(error)
    }
  )

  return instance
}

const axiosInstance = createRequest()

export const request = {
  get: <T = CommonResult>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance.get<T>(url, config).then((res) => res.data),

  post: <T = CommonResult>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance.post<T>(url, data, config).then((res) => res.data),

  put: <T = CommonResult>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance.put<T>(url, data, config).then((res) => res.data),

  delete: <T = CommonResult>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance.delete<T>(url, config).then((res) => res.data),

  patch: <T = CommonResult>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance.patch<T>(url, data, config).then((res) => res.data),
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === TOKEN_KEY && event.newValue === null) {
      router.push('/login')
    }
  })
}

export default request
