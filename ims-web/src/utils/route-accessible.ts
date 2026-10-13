/**
 * 路由可达判断（B3 新建）
 * 依据: 个人工作台-实现理解 §7.3「路由可达」策略
 *
 * 无菜单的子页面（如 /ims/workbench/todos、/ims/workbench/messages）不在 menuTree 中，
 * 但若其父路由在 menuTree 中，则允许访问。
 */
import type { MenuItem } from '@/types'

/**
 * 收集菜单树中所有路径（包括目录和叶子）。
 */
function collectAllPaths(menus: MenuItem[]): Set<string> {
  const paths = new Set<string>()
  const walk = (items: MenuItem[]) => {
    for (const item of items) {
      if (item.path) {
        paths.add(item.path)
      }
      if (item.children) {
        walk(item.children)
      }
    }
  }
  walk(menus)
  return paths
}

/**
 * 获取路由的父路径列表。
 * 例如: /ims/workbench/todos → ['/ims/workbench', '/ims', '/']
 */
function getParentPaths(route: string): string[] {
  const parts = route.split('/').filter(Boolean)
  const parents: string[] = []
  for (let i = parts.length - 1; i > 0; i--) {
    parents.push('/' + parts.slice(0, i).join('/'))
  }
  parents.push('/')
  return parents
}

/**
 * 判断路由是否可达。
 *
 * 规则：
 * 1. 路由本身在菜单树中 → 允许
 * 2. 路由的任一父路由在菜单树中 → 允许
 * 3. 否则 → 不允许
 *
 * @param route 要判断的路由路径
 * @param menus 菜单树
 * @returns 是否可达
 */
export function isRouteAccessible(route: string, menus: MenuItem[]): boolean {
  if (!route || !menus.length) return false

  const menuPaths = collectAllPaths(menus)

  // 路由本身在菜单树中
  if (menuPaths.has(route)) return true

  // 检查父路由
  const parents = getParentPaths(route)
  for (const parent of parents) {
    if (menuPaths.has(parent)) return true
  }

  return false
}
