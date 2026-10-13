/**
 * 路由可达判断（B3）
 * 依据: 个人工作台-实现理解 §7.3，以及产品复核：只看直接上一级。
 *
 * 允许访问当且仅当：
 * 1. 页面本身在菜单树内；或
 * 2. 该页是无菜单二级页，且直接父菜单在菜单树内。
 * 有自身菜单、但不在当前用户菜单树里的叶子，即使上级目录在树内，也不可访问。
 */
import type { MenuItem } from '@/types'

function collectAllPaths(menus: MenuItem[]): Set<string> {
  const paths = new Set<string>()
  const walk = (items: MenuItem[]) => {
    for (const item of items) {
      if (item.path) paths.add(normalizePath(item.path))
      if (item.children?.length) walk(item.children)
    }
  }
  walk(menus)
  return paths
}

/** 去掉 query/hash，并去掉多余的结尾斜杠。 */
export function normalizePath(route: string): string {
  const path = (route.split(/[?#]/)[0] || '').trim()
  if (path.length > 1 && path.endsWith('/')) return path.slice(0, -1)
  return path
}

/** 只取直接上一级，不继续往根走。`/ims/workbench/todos` → `/ims/workbench`。 */
export function directParentPath(route: string): string | null {
  const parts = normalizePath(route).split('/').filter(Boolean)
  if (parts.length < 2) return null
  return `/${parts.slice(0, -1).join('/')}`
}

/**
 * @param route 目标路径，可带 query
 * @param menus 当前用户菜单树
 * @param menuless 目标是否为无菜单二级页。有自身菜单的页面必须传 false。
 */
export function isRouteAccessible(route: string, menus: MenuItem[], menuless = false): boolean {
  const path = normalizePath(route)
  if (!path || !menus.length) return false

  const menuPaths = collectAllPaths(menus)
  if (menuPaths.has(path)) return true
  if (!menuless) return false

  const parent = directParentPath(path)
  return parent !== null && menuPaths.has(parent)
}
