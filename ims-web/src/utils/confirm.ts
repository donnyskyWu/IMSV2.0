/**
 * 确认对话框工具函数
 * 依据: FP-C-16 删除红色确认框
 */
import { ElMessageBox } from 'element-plus'

interface ConfirmOptions {
  title?: string
  message: string
  type?: 'warning' | 'danger' | 'info'
  confirmButtonText?: string
  cancelButtonText?: string
}

/**
 * 显示确认对话框
 * @param options 配置项
 * @returns Promise<boolean> 用户是否确认
 */
export async function confirm(options: ConfirmOptions): Promise<boolean> {
  const {
    title = '提示',
    message,
    type = 'warning',
    confirmButtonText = '确定',
    cancelButtonText = '取消',
  } = options

  const messageBoxType = type === 'danger' ? 'warning' : type

  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText,
      cancelButtonText,
      type: messageBoxType,
      confirmButtonClass: type === 'danger' ? 'el-button--danger' : '',
      distinguishCancelAndClose: true,
    })
    return true
  } catch {
    return false
  }
}

export default confirm
