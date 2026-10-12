/**
 * 真后端联通配置（fix B0b）。
 * 只跑 live-proxy.spec.ts：浏览器打 Vite，由代理转到真实 FastAPI。
 * 不复用已有 dev server，避免沿用一份没带代理的旧进程。
 */
import { defineConfig, devices } from '@playwright/test'

const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

// Playwright 传给子进程的环境变量值必须是字符串
const webServerEnv: Record<string, string> = {}
for (const [key, value] of Object.entries(process.env)) {
  if (typeof value === 'string') webServerEnv[key] = value
}
webServerEnv.VITE_API_PROXY_TARGET = proxyTarget

export default defineConfig({
  testDir: './tests',
  testMatch: /live-proxy\.spec\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'live-proxy',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: false,
    timeout: 60_000,
    env: webServerEnv,
  },
})
