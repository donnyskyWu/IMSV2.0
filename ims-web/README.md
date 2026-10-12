# IMS Web

IMS v2 前端（Vue 3 + TypeScript + Vite + Element Plus）。

```bash
npm ci
npm run dev       # http://127.0.0.1:3000
npm run lint
npm run build     # production
npm run preview   # http://127.0.0.1:4173
npm test          # Playwright
```

示例页 `/demo/*` 与 `/__routes` 只在 dev/test 提供。生产构建访问 `/demo/*` 会回到首页。
