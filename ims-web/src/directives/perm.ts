/**
 * 权限指令
 * 依据: FP-C05-01 PermissionGate
 * 用法:
 *   v-perm="'ims:system:user:create'"
 *   v-perm="['ims:system:user:create', 'ims:system:user:update']"
 *   v-perm.all="['code1', 'code2']" (全部满足)
 *   v-perm.w="'code'" (要求写权限)
 *   v-perm.d="'code'" (要求删权限)
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

// 权限码格式校验
const PERM_CODE_PATTERN = /^ims:[a-z]+:[a-z-]+:[a-z]+$/

function checkPerm(binding: DirectiveBinding): boolean {
  const authStore = useAuthStore()
  const { value, modifiers } = binding

  if (!value) {
    return true
  }

  const codes = Array.isArray(value) ? value : [value]

  // 开发环境校验权限码格式 (§2.2 #9: 使用 warn 而非 error)
  if (import.meta.env.DEV) {
    codes.forEach((code) => {
      if (typeof code === 'string' && !PERM_CODE_PATTERN.test(code)) {
        console.warn(`[v-perm] 权限码格式不符合 ims:<域>:<资源>:<动作>: ${code}`)
      }
    })
  }

  // .all 修饰符: 全部满足
  if (modifiers.all) {
    return authStore.hasAllPerm(codes)
  }

  // 默认: 任一满足
  return authStore.hasAnyPerm(codes)
}

export const vPerm: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    if (!checkPerm(binding)) {
      // 无权限时不渲染元素
      el.parentNode?.removeChild(el)
    }
  },
  updated(el: HTMLElement, binding: DirectiveBinding) {
    if (!checkPerm(binding)) {
      el.parentNode?.removeChild(el)
    }
  },
}

export default vPerm
