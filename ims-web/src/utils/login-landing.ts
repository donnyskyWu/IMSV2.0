/**
 * 登录落地与 redirect 校验（FP-B1-LG-08，裁定 21）
 * 顺序：站内且在菜单中的 redirect → 已登记的工作台（B3 之后）→ 第一个已登记叶子菜单。
 * 没有可落地页面时返回 null，调用方停在壳路径，由 AppLayout 内容区提示，不另开页面。
 */
import type { MenuItem } from '@/types'

/** 强制改密页。/user/change-password 保留给 B0b 已登记路径，页面与 /password-reset 相同。 */
export const PASSWORD_RESET_PATH = '/password-reset'
export const PASSWORD_RESET_ALIAS = '/user/change-password'

/** 壳路径。菜单为空或叶子都未登记时停在这里，不使用独立账号首页。 */
export const APP_SHELL_PATH = '/'

const PASSWORD_PATHS = new Set([PASSWORD_RESET_PATH, PASSWORD_RESET_ALIAS])

export function isPasswordPath(path: string): boolean {
  return PASSWORD_PATHS.has(path)
}

/** 只接受以 / 开头、且不是协议相对路径的站内地址。 */
export function sanitizeRedirect(value: unknown): string | null {
  if (typeof value !== 'string' || value.length === 0) return null
  if (!value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) return null
  if (value.includes('://') || value.includes('\\')) return null
  if (isPasswordPath(value.split('?')[0] || value)) return null
  return value
}

/** 按菜单树顺序收集叶子路径（目录节点本身不作为落地页）。 */
export function collectLeafPaths(menus: MenuItem[]): string[] {
  const paths: string[] = []
  const walk = (items: MenuItem[]) => {
    for (const item of items) {
      if (item.children && item.children.length > 0) {
        walk(item.children)
      } else if (item.path) {
        paths.push(item.path)
      }
    }
  }
  walk(menus)
  return paths
}

function businessRoutes(paths: string[]): Set<string> {
  return new Set(paths.filter((path) => path && path !== APP_SHELL_PATH && !path.includes(':')))
}

/**
 * 侧栏只保留路由已登记的叶子。目录在子项被滤空后一并去掉。
 * B3 之前 /ims/workbench 尚未登记，不能把这份菜单画出来。
 */
export function visibleMenus(menus: MenuItem[], registeredPaths: string[]): MenuItem[] {
  const registered = businessRoutes(registeredPaths)
  const walk = (items: MenuItem[]): MenuItem[] => {
    const visible: MenuItem[] = []
    for (const item of items) {
      if (item.children && item.children.length > 0) {
        const children = walk(item.children)
        if (children.length > 0) visible.push({ ...item, children })
        continue
      }
      // 没有 path 的目录、按钮，以及 path 未登记的叶子，都不能成为可点项。
      if (item.path && registered.has(item.path)) visible.push(item)
    }
    return visible
  }
  return walk(menus)
}

export function resolveLanding(options: {
  redirect?: unknown
  menus: MenuItem[]
  registeredPaths: string[]
}): string | null {
  const registered = businessRoutes(options.registeredPaths)
  const redirect = sanitizeRedirect(options.redirect)
  const redirectPath = redirect ? (redirect.split('?')[0] || redirect) : ''
  const leaves = collectLeafPaths(options.menus)
  // 菜单为空时停在壳路径提示，不因为工作台路由已登记就把人送进去（LG-08 ④ / LG-09）。
  if (leaves.length === 0) return null
  if (redirectPath && leaves.includes(redirectPath) && registered.has(redirectPath)) {
    return redirectPath
  }
  if (leaves.includes('/ims/workbench') && registered.has('/ims/workbench')) return '/ims/workbench'
  const first = leaves.find((path) => registered.has(path))
  return first || null
}

/** 没有业务落地页时回到壳路径，页面不跳到账号首页。 */
export function landingPath(options: {
  redirect?: unknown
  menus: MenuItem[]
  registeredPaths: string[]
}): string {
  return resolveLanding(options) ?? APP_SHELL_PATH
}
