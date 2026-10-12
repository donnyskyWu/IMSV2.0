# IMS Web

IMS v2 前端（Vue 3 + TypeScript + Vite + Element Plus）。

```bash
npm ci
npm run dev       # http://127.0.0.1:3000
npm run lint
npm run build     # production
npm run preview   # http://127.0.0.1:4173
npm test          # Playwright（不含真后端联通）
npm run test:live-proxy  # 经 Vite 代理打真实后端，需先起 API
```

开发服务器和 `vite preview` 会把 `/admin-api`、`/health` 代理到后端。默认 `http://127.0.0.1:8000`，可用环境变量 `VITE_API_PROXY_TARGET` 覆盖。

示例页 `/demo/*` 与 `/__routes` 只在 dev/test 提供。生产构建访问 `/demo/*` 会回到首页。
