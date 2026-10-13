/**
 * 待办「去处理 / 关闭」。
 * TD-03：跳转前 GET /todo/my/get，仍为 PENDING 才跳。
 * Q9：1504 落在这次查询的错误分支；非审批/审核由本人关闭，审批/审核只提示。
 */
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { todoApi, type TodoItem } from '@/api/workbench'
import { ApiError } from '@/api/request'
import { useAuthStore } from '@/stores/auth'
import { isRouteAccessible } from '@/utils/route-accessible'
import { isRegisteredMenuless } from '@/utils/menuless-route'
import { canCloseTodo } from '@/utils/todo-display'

const SOURCE_GONE = '单据已被处理或删除'

export function useTodoActions(refresh: () => void) {
  const router = useRouter()
  const authStore = useAuthStore()

  async function closeAsSelf(todo: TodoItem) {
    try {
      await todoApi.close(todo.id)
    } catch {
      // 单据已不在时关闭可能再次失败，列表仍刷新。
    }
    ElMessage.warning(SOURCE_GONE)
    refresh()
  }

  async function handleGo(todo: TodoItem) {
    try {
      const detail = await todoApi.getMyDetail(todo.id)
      if (detail.code !== 0 || !detail.data || detail.data.status !== 'PENDING') {
        ElMessage.warning('待办已处理')
        refresh()
        return
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === 1504) {
        if (canCloseTodo(todo.type)) {
          await closeAsSelf(todo)
        } else {
          ElMessage.warning(SOURCE_GONE)
        }
      }
      return
    }

    if (!todo.route) {
      ElMessage.info('暂无跳转目标')
      return
    }
    if (!isRouteAccessible(todo.route, authStore.menus, isRegisteredMenuless(todo.route))) {
      ElMessage.warning('暂无权限访问')
      return
    }
    await router.push(todo.route)
  }

  async function handleClose(todo: TodoItem) {
    if (!canCloseTodo(todo.type)) {
      ElMessage.warning('该待办需在来源单据中处理')
      return
    }

    try {
      await ElMessageBox.confirm('确定关闭该待办吗？关闭后将不再显示。', '提示', {
        confirmButtonText: '关闭',
        cancelButtonText: '取消',
        type: 'warning',
      })
      const res = await todoApi.close(todo.id)
      if (res.code === 0) {
        ElMessage.success('待办已关闭')
        refresh()
      }
    } catch (err) {
      if (err === 'cancel') return
      if (err instanceof ApiError && err.code === 1001) {
        ElMessage.warning(err.message)
      }
    }
  }

  return { handleGo, handleClose }
}
