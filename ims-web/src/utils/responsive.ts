/**
 * 响应式工具
 * 依据: 00-工作包 §2.1 Q1~Q21
 */
import { ref, onMounted, onUnmounted } from 'vue'

// 断点值 (§2.1 Q1)
export const BP_MOBILE = 768

/**
 * 判断当前是否为手机视口
 * Q1: <768px 为手机布局, >=768px 为桌面布局
 * Q11: 横屏 844×390 宽度 >=768px，按桌面布局处理
 */
export function isMobile(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < BP_MOBILE
}

/**
 * 响应式 Hook: 监听视口变化
 */
export function useResponsive() {
  const mobile = ref(isMobile())

  const handleResize = () => {
    mobile.value = isMobile()
  }

  onMounted(() => {
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
  })

  return {
    isMobile: mobile,
  }
}

/**
 * 判断是否为触控设备
 * Q2: 触控设备上悬停交互改为点击
 */
export function isTouchDevice(): boolean {
  if (typeof window === 'undefined') return false
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0
}

/**
 * 响应式 Hook: 触控设备检测
 */
export function useTouch() {
  const isTouch = ref(isTouchDevice())
  return { isTouch }
}

/**
 * 计算 Modal 宽度 (§2.1 Q7)
 * Modal 宽度 = min(档位, 100vw - 32px)，左右各留 16px 边距
 */
export function getModalWidth(size: 360 | 520 | 800): number {
  if (typeof window === 'undefined') return size
  const maxWidth = window.innerWidth - 32
  return Math.min(size, maxWidth)
}

/**
 * 计算抽屉宽度 (§2.1 Q6)
 * 手机下 FormDrawer S/M/L 都改为 100% 全屏
 */
export function getDrawerWidth(size: 'S' | 'M' | 'L'): string {
  if (isMobile()) {
    return '100%'
  }
  const widthMap = { S: '480px', M: '720px', L: '880px' }
  return widthMap[size]
}

/**
 * 计算统计卡列数 (§2.1 Q16)
 * 桌面: cols 参数 (默认 4)
 * 手机: 每行 2 列
 */
export function getStatCols(cols: number = 4): number {
  return isMobile() ? 2 : cols
}
