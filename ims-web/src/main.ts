/**
 * IMS 前端应用入口
 * 依据: 00-工作包, 02-前端基础层清单
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { vPerm } from './directives/perm'

// 样式
import 'element-plus/dist/index.css'
import './styles/global.scss'
import './styles/element-theme.scss'
import './styles/auth-form.scss'

const app = createApp(App)

// Pinia
app.use(createPinia())

// Router
app.use(router)

// Element Plus
app.use(ElementPlus, {
  locale: zhCn,
})

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 权限指令
app.directive('perm', vPerm)

// Q12: viewport 允许用户缩放
// 在 index.html 中设置 <meta name="viewport" content="width=device-width, initial-scale=1.0">

app.mount('#app')
