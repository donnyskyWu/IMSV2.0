/**

 * auth API - Auto-generated from OpenAPI

 * Generated at: 2026-10-12T07:15:45.837106

 * DO NOT EDIT MANUALLY

 */



import { request } from '../request';



// API Functions

/**
 * 账号密码登录
 */
export async function login(data: LoginRequest): Promise<CommonResult_LoginResponse_> {
  const url = '/admin-api/ims/auth/login';
  return request(url, { method: 'POST', data });
}

/**
 * 登出
 */
export async function logout(): Promise<CommonResult> {
  const url = '/admin-api/ims/auth/logout';
  return request(url, { method: 'POST' });
}

/**
 * 获取当前用户信息
 */
export async function getMe(): Promise<CommonResult_MeResponse_> {
  const url = '/admin-api/ims/auth/me';
  return request(url, { method: 'GET' });
}

/**
 * 刷新令牌
 */
export async function refreshToken(data: RefreshTokenRequest): Promise<CommonResult_LoginResponse_> {
  const url = '/admin-api/ims/auth/refresh-token';
  return request(url, { method: 'POST', data });
}

/**
 * 钉钉SSO回调
 */
export async function getSsoDingtalkCallback(params: { authCode: string; state: string }): Promise<any> {
  const url = '/admin-api/ims/auth/sso/dingtalk/callback';
  return request(url, { method: 'GET', params });
}

/**
 * 钉钉SSO跳转
 */
export async function getSsoDingtalkRedirect(params: { redirect?: string }): Promise<any> {
  const url = '/admin-api/ims/auth/sso/dingtalk/redirect';
  return request(url, { method: 'GET', params });
}