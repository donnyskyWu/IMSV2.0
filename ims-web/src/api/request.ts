/**
 * HTTP Request module (FP-A05-01)
 * 
 * Base request function for API calls.
 * This is the ONLY place where /admin-api is allowed in frontend code.
 * 
 * Rules per FP-A05-01:
 * - Frontend business code must NOT contain /admin-api strings
 * - Only this file and generated/ can reference the API prefix
 */

import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios';

// API base URL - the only place /admin-api should appear
const API_BASE_URL = '/admin-api/ims';

// Axios instance
const instance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add trace ID
    config.headers['X-Trace-Id'] = crypto.randomUUID();
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    const { code, msg, data } = response.data;
    
    // Success
    if (code === 0) {
      return response.data;
    }
    
    // Handle specific error codes
    switch (code) {
      case 1002: // Session expired
      case 1003: // Kicked out
        // Clear tokens and redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        break;
      
      case 1008: // No permission
        // Show no permission message
        console.warn('No permission:', msg);
        break;
      
      case 1001: // Validation error
        // fieldErrors will be in data
        console.warn('Validation error:', data?.fieldErrors);
        break;
    }
    
    // Reject with error info
    return Promise.reject({ code, msg, data });
  },
  (error) => {
    // Network or server error
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      window.location.href = '/login';
    }
    
    return Promise.reject({
      code: 5007,
      msg: '网络错误，请稍后重试',
      data: null,
    });
  }
);

// Request options type
export interface RequestOptions extends AxiosRequestConfig {
  params?: Record<string, any>;
  data?: any;
}

// Unified request function
export async function request<T = any>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  const response = await instance.request({
    url,
    ...options,
  });
  return response as T;
}

// Export instance for advanced usage
export { instance as axios };
