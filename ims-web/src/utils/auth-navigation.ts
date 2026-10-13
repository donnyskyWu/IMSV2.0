/**
 * 路由守卫拉取 /me 时先静默刷新。
 * 这段时间请求层只清令牌、不自己跳转，避免把 refresh token 清掉之前就改掉地址。
 */
let depth = 0

export function beginAuthNavigation(): void {
  depth += 1
}

export function endAuthNavigation(): void {
  depth = Math.max(0, depth - 1)
}

export function isAuthNavigation(): boolean {
  return depth > 0
}
