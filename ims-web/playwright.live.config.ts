/**
 * 真后端联通配置（fix B0b）。
 * 只跑 live-proxy.spec.ts：浏览器打 Vite，由代理转到真实 FastAPI。
 * 不复用已有 dev server，避免沿用一份没带代理的旧进程。
 *
 * 登录账号只读 ims-backend/tools/seed/users.py 的 E2E_USERNAME / E2E_PASSWORD。
 * 改名时只改那一处，这里不要再写死账号。
 */
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig, devices } from '@playwright/test'

const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
const backendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../ims-backend')

function loadSeedAccount(): void {
  const python = process.env.PYTHON || 'python3'
  const pythonEnv: Record<string, string> = { PYTHONPATH: backendRoot }
  for (const [key, value] of Object.entries(process.env)) {
    if (typeof value === 'string') pythonEnv[key] = value
  }
  const output = execFileSync(
    python,
    [
      '-c',
      'from tools.seed.users import E2E_USERNAME, E2E_PASSWORD; print(E2E_USERNAME); print(E2E_PASSWORD)',
    ],
    {
      cwd: backendRoot,
      encoding: 'utf8',
      env: pythonEnv,
    },
  )
  const [username, password] = output.trim().split(/\r?\n/)
  if (!username || !password) {
    throw new Error('未能从 tools.seed.users 读到 E2E 账号')
  }
  process.env.E2E_SEED_USERNAME = username
  process.env.E2E_SEED_PASSWORD = password
}

loadSeedAccount()

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
