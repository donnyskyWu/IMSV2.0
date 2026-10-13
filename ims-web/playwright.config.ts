/**
 * Playwright 测试配置
 * 依据: 02-验证用例.md
 * 视口:
 *   - 桌面: 1440×900
 *   - 移动: 390×844 (Chromium & WebKit)
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  // 真后端联通在 playwright.live.config.ts 里单独跑，避免没起 API 时把组件用例打红
  testIgnore: /live-proxy\.spec\.ts/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    // 桌面视口 1440×900
    {
      name: 'desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },

    // 移动视口 390×844 Chromium
    {
      name: 'mobile-390-chromium',
      use: {
        ...devices['iPhone 14'],
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
      },
    },

    // 移动视口 390×844 WebKit
    {
      name: 'mobile-390-webkit',
      use: {
        ...devices['iPhone 14'],
        browserName: 'webkit',
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
      },
    },

    // 生产构建：VC-M-34 与 B1 无菜单登录冒烟。vite build --mode production + vite preview
    {
      name: 'prod-build',
      use: {
        ...devices['iPhone 14'],
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
        baseURL: 'http://127.0.0.1:4173',
      },
      testMatch: /mobile\.spec\.ts|b1-prod-smoke\.spec\.ts/,
      grep: /VC-M-34|B1-PROD-01/,
    },
  ],

  // 开发服务器供桌面/移动用例；独立的 production preview 供 VC-M-34
  webServer: [
    {
      // 组件用例自己 mock 网络。关掉代理，避免没起后端时 502 变成 console.error
      command: 'VITE_API_PROXY_TARGET=off npm run dev',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'VITE_API_PROXY_TARGET=off npm run build && VITE_API_PROXY_TARGET=off npm run preview',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
})
