/**

 * common API - Auto-generated from OpenAPI

 * Generated at: 2026-10-12T07:15:45.837507

 * DO NOT EDIT MANUALLY

 */



import { request } from '../request';



// API Functions

/**
 * Health Check
 */
export async function getHealth(): Promise<CommonResult_HealthData_> {
  const url = '/health';
  return request(url, { method: 'GET' });
}