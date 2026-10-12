/**
 * 前端纯函数单测。覆盖率只统计登录落地、错误文案、改密规则这三个工具文件。
 * 80%/90% 门槛在 IMS-单元测试Checklist 里是后端新增代码与 P0 Service；
 * 这三个文件单独要求行、分支、函数都 ≥ 90%。
 */
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

const root = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(root, 'src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.unit.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: [
        'src/utils/login-landing.ts',
        'src/utils/login-errors.ts',
        'src/utils/password-rules.ts',
      ],
      thresholds: {
        lines: 90,
        branches: 90,
        functions: 90,
        statements: 90,
      },
    },
  },
})
