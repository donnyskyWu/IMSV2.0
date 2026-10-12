import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import type { Plugin } from 'vite'

/**
 * FP-R-09: /__routes 端点 (§2.2 #9)
 * 仅在 test 构建中提供，不需要鉴权
 * 返回格式: [{path, name, meta}]
 */
function routesEndpointPlugin(): Plugin {
  return {
    name: 'routes-endpoint',
    configureServer(server) {
      server.middlewares.use('/__routes', (_req, res) => {
        // 返回路由清单 (实际值在运行时由前端获取)
        // 这里返回静态定义，因为 SSR 不可用
        const routes = [
          { path: '/demo/tokens', name: 'DemoTokens', meta: { title: 'Token 演示' } },
          { path: '/demo/layout', name: 'DemoLayout', meta: { title: '布局演示' } },
          { path: '/demo/list', name: 'DemoList', meta: { title: '列表演示' } },
          { path: '/demo/tabs-list', name: 'DemoTabsList', meta: { title: 'Tab 列表演示' } },
          { path: '/demo/form', name: 'DemoForm', meta: { title: '表单演示' } },
          { path: '/demo/selectors', name: 'DemoSelectors', meta: { title: '选择器演示' } },
          { path: '/demo/files', name: 'DemoFiles', meta: { title: '文件演示' } },
          { path: '/demo/display', name: 'DemoDisplay', meta: { title: '展示组件' } },
          { path: '/demo/dept-tree', name: 'DemoDeptTree', meta: { title: '部门树' } },
          { path: '/demo/left-tree-right-table', name: 'DemoLeftTreeRightTable', meta: { title: '左树右表' } },
          { path: '/demo/workbench', name: 'DemoWorkbench', meta: { title: '工作台', menuless: true } },
          { path: '/demo/fill', name: 'DemoFill', meta: { title: '填报页', menuless: true } },
          { path: '/demo/request', name: 'DemoRequest', meta: { title: '请求演示' } },
        ]
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(routes))
      })
    },
  }
}

/**
 * 开发服务器和 preview 共用的后端代理。
 * 浏览器访问 /admin-api、/health 时转到 FastAPI。
 * 目标地址用 VITE_API_PROXY_TARGET 覆盖，默认 http://127.0.0.1:8000。
 * 不配代理时这两个前缀会落到 Vite 自己，开发环境前后端对不上。
 */
function backendProxy(mode: string): Record<string, { target: string; changeOrigin: boolean }> | undefined {
  const fileEnv = loadEnv(mode, process.cwd(), '')
  const raw = process.env.VITE_API_PROXY_TARGET ?? fileEnv.VITE_API_PROXY_TARGET
  // off：只给「不连后端」的组件用例用。不设或设成地址时才转发。
  if (raw === 'off') return undefined
  const target = raw || 'http://127.0.0.1:8000'
  return {
    '/admin-api': { target, changeOrigin: true },
    '/health': { target, changeOrigin: true },
  }
}

export default defineConfig(({ mode }) => {
  const isTest = mode === 'test' || mode === 'development'
  const proxy = backendProxy(mode)

  return {
    plugins: [
      vue(),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia'],
        resolvers: [ElementPlusResolver()],
        // 生产构建与 dev 并行时不要重写 d.ts，避免和开发服务器抢文件
        dts: mode === 'development' ? 'src/auto-imports.d.ts' : false,
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: mode === 'development' ? 'src/components.d.ts' : false,
      }),
      // FP-R-09: 仅 test 构建提供 /__routes
      ...(isTest ? [routesEndpointPlugin()] : []),
    ],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, 'src'),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/styles/variables.scss" as *;`,
        },
      },
    },
    // 开发服务器与生产构建并行时分开缓存目录，避免互相覆盖
    cacheDir: mode === 'development' ? 'node_modules/.vite' : 'node_modules/.vite-build',
    // 登录页和布局是懒加载的。冷缓存第一次打开时，这些依赖不在入口扫描里，
    // Vite 会临时预构建并整页重载，把正在进行的登录导航打断。
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'axios',
        'element-plus',
        'element-plus/es',
        'element-plus/es/locale/lang/zh-cn',
        '@element-plus/icons-vue',
        // 冷启动日志里实际触发 reloading 的样式，以及登录/布局直接用到的消息组件
        ...[
          'avatar',
          'badge',
          'base',
          'button',
          'dropdown',
          'dropdown-item',
          'dropdown-menu',
          'form',
          'form-item',
          'icon',
          'input',
          'menu',
          'menu-item',
          'message',
          'message-box',
          'progress',
          'scrollbar',
          'sub-menu',
          'table',
          'table-column',
        ].map((name) => `element-plus/es/components/${name}/style/css`),
      ],
    },
    server: {
      port: 3000,
      host: '127.0.0.1',
      strictPort: true,
      // 与 preview 使用同一份代理，避免预览环境和开发环境行为不一致
      ...(proxy ? { proxy } : {}),
    },
    preview: {
      port: 4173,
      host: '127.0.0.1',
      strictPort: true,
      ...(proxy ? { proxy } : {}),
    },
  }
})
