/**
 * 路由表里标记了 menuless 的页面才享受「直接父菜单在树内即可访问」。
 * 有自身菜单的叶子不走这条例外。
 */
import router from '@/router'

export function isRegisteredMenuless(route: string): boolean {
  const path = (route.split(/[?#]/)[0] || '').replace(/\/$/, '') || '/'
  return router.getRoutes().some((item) => item.path === path && item.meta?.menuless === true)
}
