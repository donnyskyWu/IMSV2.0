/**
 * 路由可达：页面在菜单树内，或无菜单二级页且直接父菜单在树内。
 */
import { describe, expect, it } from 'vitest'
import type { MenuItem } from '@/types'
import { directParentPath, isRouteAccessible } from './route-accessible'

function item(path: string, name: string, children: MenuItem[] = []): MenuItem {
  return { id: path, name, path, children }
}

describe('isRouteAccessible', () => {
  const workbench = [item('/ims/workbench', '个人工作台')]
  const authDirOnly = [item('/ims/auth', '权限管理')]

  it('页面自身在菜单树内则可访问', () => {
    expect(isRouteAccessible('/ims/workbench', workbench)).toBe(true)
    expect(isRouteAccessible('/ims/workbench?from=home', workbench)).toBe(true)
  })

  it('无菜单二级页且直接父菜单在树内则可访问', () => {
    expect(isRouteAccessible('/ims/workbench/todos', workbench, true)).toBe(true)
    expect(isRouteAccessible('/ims/workbench/messages', workbench, true)).toBe(true)
  })

  it('无菜单页只认直接上一级，祖父在树内不够', () => {
    const ancestorOnly = [item('/ims', 'IMS')]
    expect(directParentPath('/ims/workbench/todos')).toBe('/ims/workbench')
    expect(isRouteAccessible('/ims/workbench/todos', ancestorOnly, true)).toBe(false)
    expect(isRouteAccessible('/ims/workbench/todos', [{ id: 'root', name: '根', path: '/' }], true)).toBe(false)
  })

  it('目录在树、叶子页有自身菜单但不在树 → 不可访问', () => {
    expect(isRouteAccessible('/ims/auth/org', authDirOnly, false)).toBe(false)
    expect(isRouteAccessible('/ims/auth/org', authDirOnly)).toBe(false)
    expect(isRouteAccessible('/ims/auth/position', [
      item('/ims/auth', '权限管理', [item('/ims/auth/org', '组织架构同步')]),
    ])).toBe(false)
  })

  it('叶子在树内即使同时声明无菜单也允许', () => {
    const tree = [item('/ims/auth', '权限管理', [item('/ims/auth/org', '组织架构同步')])]
    expect(isRouteAccessible('/ims/auth/org', tree, false)).toBe(true)
  })

  it('空菜单或空路径不可访问', () => {
    expect(isRouteAccessible('/ims/workbench/todos', [], true)).toBe(false)
    expect(isRouteAccessible('', workbench, true)).toBe(false)
  })
})
