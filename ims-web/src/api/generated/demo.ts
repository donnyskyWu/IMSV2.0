/**

 * demo API - Auto-generated from OpenAPI

 * Generated at: 2026-10-12T07:15:45.837260

 * DO NOT EDIT MANUALLY

 */



import { request } from '../request';



// API Functions

/**
 * 测试错误码响应
 */
export async function getError(params: { code: number }): Promise<CommonResult> {
  const url = '/admin-api/ims/demo/error';
  return request(url, { method: 'GET', params });
}