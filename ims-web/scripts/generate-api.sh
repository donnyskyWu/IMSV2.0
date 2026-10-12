#!/bin/bash
# 从 B0a 的 OpenAPI 契约生成 TypeScript API 客户端
# 依据: B0b 工作包 §5, FP-R-01~07
#
# 使用方法:
#   ./scripts/generate-api.sh [branch]
#
# 参数:
#   branch - Git 分支名 (默认: main)
#            B0a 合入 main 前使用 cursor/b0a-backend-framework-c870
#
# 输出:
#   src/api/generated/ - 生成的 API 客户端代码

set -e

BRANCH="${1:-main}"
OPENAPI_PATH="ims-backend/openapi.json"
OUTPUT_DIR="src/api/generated"

echo "🔄 从分支 $BRANCH 获取 OpenAPI 契约..."

# 确保在 ims-web 目录下运行
cd "$(dirname "$0")/.."

# 从远程分支获取 openapi.json
git fetch origin "$BRANCH" 2>/dev/null || true
SPEC_CONTENT=$(git show "origin/$BRANCH:$OPENAPI_PATH" 2>/dev/null) || {
  echo "❌ 无法从 origin/$BRANCH 获取 $OPENAPI_PATH"
  echo "   请确保分支存在且包含该文件"
  exit 1
}

# 创建临时文件
TEMP_SPEC=$(mktemp)
echo "$SPEC_CONTENT" > "$TEMP_SPEC"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 使用 openapi-typescript 生成类型
echo "📝 生成 TypeScript 类型定义..."
npx openapi-typescript "$TEMP_SPEC" -o "$OUTPUT_DIR/api-types.ts" --enum

# 生成 API 客户端
echo "🛠️ 生成 API 客户端..."
cat > "$OUTPUT_DIR/index.ts" << 'EOF'
/**
 * IMS API 客户端 (自动生成)
 * 来源: ims-backend/openapi.json
 * 生成时间: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
 *
 * 请勿手动修改此文件，运行 scripts/generate-api.sh 重新生成
 */
export * from './api-types'
export * from './client'
EOF

# 生成客户端封装
cat > "$OUTPUT_DIR/client.ts" << 'CLIENTEOF'
/**
 * API 客户端封装
 * 提供类型安全的 API 调用方法
 */
import { request } from '../request'
import type { paths, components } from './api-types'

type Schemas = components['schemas']

// 认证相关
export const authApi = {
  login: (data: { username: string; password: string }) =>
    request.post<Schemas['CommonResult_LoginResponse_']>(
      '/admin-api/ims/auth/login',
      data
    ),

  logout: () =>
    request.post<Schemas['CommonResult']>('/admin-api/ims/auth/logout'),

  refreshToken: (data: { refreshToken: string }) =>
    request.post<Schemas['CommonResult_LoginResponse_']>(
      '/admin-api/ims/auth/refresh-token',
      data
    ),

  me: () =>
    request.get<Schemas['CommonResult_MeResponse_']>('/admin-api/ims/auth/me'),
}

// 字典相关
export const dictApi = {
  getTypeList: () =>
    request.get<Schemas['CommonResult_list_DictTypeItem__']>(
      '/admin-api/ims/system/dict-type/list'
    ),

  getDataList: (params: { dictType: string }) =>
    request.get<Schemas['CommonResult_list_DictDataItem__']>(
      '/admin-api/ims/system/dict-data/simple-list',
      { params }
    ),
}

// 部门相关
export const deptApi = {
  getTree: () =>
    request.get<Schemas['CommonResult_list_DeptTreeNode__']>(
      '/admin-api/ims/system/dept/tree'
    ),

  create: (data: Schemas['DeptCreateRequest']) =>
    request.post<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/create',
      data
    ),

  update: (data: Schemas['DeptUpdateRequest']) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/update',
      data
    ),

  move: (data: Schemas['DeptMoveRequest']) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/move',
      data
    ),

  updateStatus: (data: { id: string; status: number }) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/update-status',
      data
    ),

  delete: (id: string) =>
    request.delete<Schemas['CommonResult']>(
      '/admin-api/ims/system/dept/delete',
      { params: { id } }
    ),

  confirmOrphan: (id: string) =>
    request.put<Schemas['CommonResult_DeptResponse_']>(
      '/admin-api/ims/system/dept/confirm-orphan',
      { id }
    ),
}

// 用户相关
export const userApi = {
  getPage: (params: {
    pageNo?: number
    pageSize?: number
    deptId?: string
    includeChildren?: boolean
    keyword?: string
    status?: number
  }) =>
    request.get<Schemas['CommonResult_PageResult_UserListItem__']>(
      '/admin-api/ims/system/user/page',
      { params }
    ),

  getSimplePage: (params: {
    pageNo?: number
    pageSize?: number
    keyword?: string
  }) =>
    request.get<Schemas['CommonResult_PageResult_UserSimpleItem__']>(
      '/admin-api/ims/system/user/simple-page',
      { params }
    ),

  create: (data: Schemas['UserCreateRequest']) =>
    request.post<Schemas['CommonResult_UserListItem_']>(
      '/admin-api/ims/system/user/create',
      data
    ),

  delete: (id: string) =>
    request.delete<Schemas['CommonResult']>(
      '/admin-api/ims/system/user/delete',
      { params: { id } }
    ),

  updateDepts: (data: Schemas['UserUpdateDeptsRequest']) =>
    request.put<Schemas['CommonResult_UserListItem_']>(
      '/admin-api/ims/system/user/update-depts',
      data
    ),
}

// 角色相关
export const roleApi = {
  getSimpleList: () =>
    request.get<Schemas['CommonResult_list_RoleSimpleItem__']>(
      '/admin-api/ims/system/role/simple-list'
    ),
}

// 组织同步相关
export const orgSyncApi = {
  getLatestBatch: () =>
    request.get<Schemas['CommonResult_OrgSyncBatchItem_']>(
      '/admin-api/ims/system/org-sync/latest-batch'
    ),

  reconcile: () =>
    request.post<Schemas['CommonResult_OrgSyncBatchItem_']>(
      '/admin-api/ims/system/org-sync/reconcile'
    ),
}

// 演示错误接口 (用于测试错误处理)
export const demoApi = {
  triggerError: (params: { code: number }) =>
    request.get<Schemas['CommonResult']>(
      '/admin-api/ims/demo/error',
      { params }
    ),
}
CLIENTEOF

# 清理临时文件
rm -f "$TEMP_SPEC"

echo "✅ API 客户端生成完成: $OUTPUT_DIR/"
echo "   - api-types.ts: OpenAPI 类型定义"
echo "   - client.ts: API 客户端方法"
echo "   - index.ts: 导出入口"
