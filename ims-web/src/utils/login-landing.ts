/**
 * 登录落地与 redirect 校验（FP-B1-LG-01 / LG-08）
 * redirect 只接受站内相对路径；落地顺序：合法且在菜单中的 redirect → 已登记的工作台 → 第一个已登记叶子菜单 → 账号首页。
 */
import type { MenuItem } from '@/types'

/** 强制改密页。/user/change-password 保留给 B0b 已登记路径，页面与 /password-reset 相同。 */
export const PASSWORD_RESET_PATH = '/password-reset'
export const PASSWORD_RESET_ALIAS = '/user/change-password'
export const ACCOUNT_HOME_PATH = '/account/home'

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

export function resolveLanding(options: {
  redirect?: unknown
  menus: MenuItem[]
  registeredPaths: string[]
}): string {
  const registered = new Set(options.registeredPaths)
  const redirect = sanitizeRedirect(options.redirect)
  const leaves = collectLeafPaths(options.menus)
  if (redirect && leaves.includes(redirect.split('?')[0] || redirect) && registered.has(redirect.split('?')[0] || redirect)) {
    return redirect
  }
  if (registered.has('/ims/workbench')) return '/ims/workbench'
  const first = leaves.find((path) => registered.has(path))
  if (first) return first
  return ACCOUNT_HOME_PATH
}
