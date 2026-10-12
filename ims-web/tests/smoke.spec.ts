/**
 * 冒烟测试: 遍历所有 /demo/* 路由
 * 依据: 02-验证用例.md
 * 排除登录页
 */
import { test, expect } from '@playwright/test'

// 通过 /__routes 获取路由清单
async function getDemoRoutes(request: import('@playwright/test').APIRequestContext) {
  const response = await request.get('/__routes')
  const routes = await response.json()
  return routes.filter((r: { path: string }) => r.path.startsWith('/demo/'))
}

test.describe('冒烟测试 - Demo 页面可访问', () => {
  test('所有 /demo/* 页面应成功加载', async ({ page, request }) => {
    const routes = await getDemoRoutes(request)
    expect(routes.length).toBeGreaterThan(0)

    for (const route of routes) {
      await test.step(`访问 ${route.path}`, async () => {
        await page.goto(route.path)
        
        // 等待页面加载 (等待 AppLayout 或 PageHeader 出现)
        await page.waitForSelector('.app-layout, .page-header', { timeout: 10000 })
        
        // 不应有致命错误
        const errorDialog = page.locator('.el-message-box--error')
        await expect(errorDialog).not.toBeVisible()
        
        // 不应有 Vue 未捕获错误
        // (console.error 检查在 CI 中配置)
      })
    }
  })
})
