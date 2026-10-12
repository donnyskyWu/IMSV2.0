/**
 * FP-R-09: /__routes 端点测试
 */
import { test, expect } from '@playwright/test'

test.describe('/__routes 端点', () => {
  test('应返回路由清单 JSON', async ({ request }) => {
    const response = await request.get('/__routes')
    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toContain('application/json')

    const routes = await response.json()
    expect(Array.isArray(routes)).toBe(true)
    expect(routes.length).toBeGreaterThan(0)

    // 每个路由应有 path, name, meta
    for (const route of routes) {
      expect(route).toHaveProperty('path')
      expect(route).toHaveProperty('name')
      expect(route).toHaveProperty('meta')
      expect(typeof route.path).toBe('string')
      expect(route.path.startsWith('/demo/')).toBe(true)
    }
  })

  test('应包含所有 /demo/* 路由', async ({ request }) => {
    const response = await request.get('/__routes')
    const routes = await response.json()
    const paths = routes.map((r: { path: string }) => r.path)

    // 验证必需的 demo 路由
    const requiredPaths = [
      '/demo/tokens',
      '/demo/layout',
      '/demo/list',
      '/demo/form',
      '/demo/selectors',
      '/demo/files',
      '/demo/display',
      '/demo/dept-tree',
      '/demo/left-tree-right-table',
      '/demo/workbench',
    ]

    for (const path of requiredPaths) {
      expect(paths).toContain(path)
    }
  })
})
