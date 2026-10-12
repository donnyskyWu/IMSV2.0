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
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(callback: (token: string) => void) {
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

function redirectToLogin(message = '登录已失效，请重新登录'): void {
  clearTokens()
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
        return Promise.reject(new Error(result.msg || 'kicked'))
      }

      if (result.code === ErrorCode.TOKEN_EXPIRED) {
        const expired = Object.assign(new Error('token expired'), {
          isTokenExpired: true,
          config: response.config,
          response,
        })
        return Promise.reject(expired)
      }

      handleErrorCode(result.code, result.msg)
      return Promise.reject(new Error(result.msg || '请求失败'))
    },
    async (error: AxiosError & { isTokenExpired?: boolean }) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

      if (error.isTokenExpired && originalRequest && !originalRequest._retry) {
        if (isRefreshing) {
          return new Promise((resolve) => {
            addRefreshSubscriber((token) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`
              }
              resolve(instance(originalRequest))
            })
          })
        }

        originalRequest._retry = true
        isRefreshing = true

        try {
          const newToken = await refreshAccessToken()
          if (newToken) {
            onRefreshed(newToken)
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }
            return instance(originalRequest)
          } else {
            redirectToLogin()
            return Promise.reject(error)
          }
        } finally {
          isRefreshing = false
        }
      }

      if (error.response?.status === 401) {
        redirectToLogin()
        return Promise.reject(error)
      }

      if (!error.response) {
        ElMessage.error('网络异常，请检查网络后重试')
        return Promise.reject(error)
      }

      const result = error.response?.data as CommonResult | undefined
      if (result?.code) {
        handleErrorCode(result.code, result.msg)
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
