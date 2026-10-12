/**
 * FP-B1-LG-08 落地顺序单测。
 */
import { describe, expect, it } from 'vitest'
import type { MenuItem } from '@/types'
import {
  APP_SHELL_PATH,
  collectLeafPaths,
  isPasswordPath,
  landingPath,
  resolveLanding,
  sanitizeRedirect,
} from './login-landing'

const registered = ['/demo/tokens', '/demo/list', '/ims/workbench', APP_SHELL_PATH, '/:pathMatch(.*)*']

function leaf(path: string, name: string): MenuItem {
  return { id: path, name, path, children: [] }
}

describe('sanitizeRedirect', () => {
  it('拒绝外站、协议相对路径和改密页', () => {
    expect(sanitizeRedirect(null)).toBeNull()
    expect(sanitizeRedirect('')).toBeNull()
    expect(sanitizeRedirect('https://www.baidu.com')).toBeNull()
    expect(sanitizeRedirect('//evil.test')).toBeNull()
    expect(sanitizeRedirect('/\\evil')).toBeNull()
    expect(sanitizeRedirect('/ok\\bad')).toBeNull()
    expect(sanitizeRedirect('/path/http://x')).toBeNull()
    expect(sanitizeRedirect('/password-reset')).toBeNull()
    expect(sanitizeRedirect('/user/change-password?from=1')).toBeNull()
  })

  it('保留站内路径', () => {
    expect(sanitizeRedirect('/demo/list')).toBe('/demo/list')
    expect(sanitizeRedirect('/demo/list?tab=1')).toBe('/demo/list?tab=1')
    expect(isPasswordPath('/password-reset')).toBe(true)
    expect(isPasswordPath('/demo/list')).toBe(false)
  })
})

describe('collectLeafPaths', () => {
  it('只收集叶子，目录节点不落地', () => {
    const menus: MenuItem[] = [
      {
        id: 'dir',
        name: '权限管理',
        path: '/ims/auth',
        children: [leaf('/ims/auth/org', '组织'), leaf('/ims/auth/position', '岗位')],
      },
      { id: 'empty', name: '空目录', children: [] },
      { id: 'bare', name: '无路径' },
    ]
    expect(collectLeafPaths(menus)).toEqual(['/ims/auth/org', '/ims/auth/position'])
  })
})

describe('resolveLanding', () => {
  const menus = [leaf('/demo/tokens', 'Token'), leaf('/demo/list', '列表'), leaf('/ims/workbench', '工作台')]

  it('先用菜单内 redirect，再工作台，再第一个已登记叶子', () => {
    expect(resolveLanding({
      redirect: '/demo/list?x=1',
      menus,
      registeredPaths: registered,
    })).toBe('/demo/list')
    expect(resolveLanding({
      redirect: 'https://www.baidu.com',
      menus,
      registeredPaths: registered,
    })).toBe('/ims/workbench')
    expect(resolveLanding({
      redirect: '/ims/workbench',
      menus: [leaf('/ims/workbench', '工作台'), leaf('/demo/tokens', 'Token')],
      registeredPaths: ['/demo/tokens', '/demo/list'],
    })).toBe('/demo/tokens')
  })

  it('工作台未登记或菜单为空时不跳页', () => {
    expect(resolveLanding({
      menus: [leaf('/ims/workbench', '工作台')],
      registeredPaths: ['/demo/tokens'],
    })).toBeNull()
    expect(resolveLanding({
      menus: [],
      registeredPaths: registered,
    })).toBeNull()
    expect(landingPath({ menus: [], registeredPaths: registered })).toBe(APP_SHELL_PATH)
  })
})
