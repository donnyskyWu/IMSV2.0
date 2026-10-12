# IMS v2 Technical Constraints

> 版本: v1.0  
> 更新: 2026-10-12  
> 维护: IMS 技术团队

本文档记录 IMS v2 的技术约束和关键技术决策，作为开发和评审的参考标准。

## 1. 数据库约束

### 1.1 主键策略
- 所有业务表使用 `BIGINT` 自增主键
- `id` 字段任何接口不可修改（错误码 1211）
- 迁移数据保留原主键，序列起点 = 最大值 + 1
- 所有 `id` 和 `*Id` 字段在 API 输出时统一为字符串（D2 决策）

### 1.2 审计字段 (FP-B01-01)
所有 `ims_*` 业务表继承 `AuditBase`，包含：
- `id`: BIGINT 自增
- `tenant_id`: BIGINT NOT NULL（租户隔离）
- `creator`, `create_time`: 创建人和时间
- `updater`, `update_time`: 更新人和时间
- `deleted`: BIGINT NOT NULL DEFAULT 0（逻辑删除用 deleted=id）

### 1.3 逻辑删除
- 删除时设置 `deleted = id`（非 1），支持同业务编码重建
- 唯一键模式: `(tenant_id, business_code, deleted)`
- 查询条件: `deleted = 0` 表示未删除

### 1.4 引用完整性 (D2 决策)
- 不使用物理外键，在应用层校验引用
- 引用不存在 → 1500
- 引用已停用 → 1501
- 删除/停用被引用 → 1502
- 引用跨租户 → 1504

## 2. 时间处理 (D4 决策)

### 2.1 时钟注入
- **禁止**直接调用 `datetime.now()`
- 必须使用 `app/core/clock.py` 中的 `get_now()` 函数
- 测试可通过 `set_clock()` 注入固定时间

### 2.2 时区规范
- 数据库存储: 北京时间 (DATETIME，无时区)
- API 输出: ISO 8601 带时区 `+08:00`，如 `2026-10-12T10:30:00+08:00`
- API 输入: 接受带/不带时区，不带时区视为北京时间

## 3. 认证与会话 (FW-D01)

### 3.1 会话机制 (D5 决策)
- Access Token: JWT (2小时有效期)
- Refresh Token: 随机串 (7天有效期)
- 会话存储: Redis `ims:session:<sid>`
- 每用户最多 3 个并发会话，新登录踢掉最早会话

### 3.2 密码策略
- 长度 8-32 位，至少含字母和数字
- bcrypt 哈希 (cost=10)
- 连续 5 次失败锁定 15 分钟

### 3.3 令牌刷新
- 刷新成功签发新 access + 新 refresh
- 旧 refresh 立即失效（轮换机制）
- 重复使用旧 refresh → 1002

## 4. 权限控制 (FW-D03)

### 4.1 权限码格式
- 统一格式: `ims:<domain>:<resource>[:<action>]`
- 正则: `^ims(:[a-z][a-z0-9-]*){2,3}$`

### 4.2 数据范围 (FW-D04)
- 范围类型: `ALL` / `DEPT` / `IP_GROUP` / `SELF`
- 多角色取**并集**
- 未配置数据范围 → 1008（无数据可见）

### 4.3 禁止角色名判断 (静态检查)
- 业务代码禁止出现 `role_key`、`role.name` 的条件判断
- 禁止硬编码 `"R1"` ~ `"R11"`、`"admin"` 等

## 5. API 规范

### 5.1 路由前缀
- 业务接口: `/admin-api/ims/<domain>/...`
- 例外: `/health` (匿名)

### 5.2 响应格式
```json
{
  "code": 0,
  "msg": "成功",
  "data": { ... }
}
```
- 业务结果一律 HTTP 200
- 仅 1002/1003 返回 HTTP 401

### 5.3 分页参数
- `pageNo`: 默认 1，必须 ≥ 1
- `pageSize`: 默认 10，范围 1-100
- 超过 100 → 1001（拒绝而非截断）

### 5.4 命名转换
- API: camelCase
- 数据库: snake_case
- 由 Schema 基类自动转换

## 6. 字典与参数 (FW-B07)

### 6.1 字典类型格式
- 格式: `^dict_[a-z][a-z0-9_]*$`
- 例如: `dict_user_status`, `dict_platform_type`

### 6.2 字典值格式
- 格式: `^[A-Z][A-Z0-9_]*$`
- 例如: `ACTIVE`, `PENDING_REVIEW`

### 6.3 颜色类型
8 种语义色: `primary`(蓝) / `success`(绿) / `warning`(橙) / `danger`(红) / `neutral`(灰) / `info`(青) / `purple`(紫) / `yellow`(黄)

## 7. 外部集成 (FW-H04)

### 7.1 适配器模式
- 每个外部系统: 接口 + Real/Mock 实现
- 配置: `integrations.<system>.mode = real|mock`
- 测试环境全部使用 Mock

### 7.2 超时与熔断
- 默认超时: 10 秒
- 幂等读操作重试: 最多 2 次
- 熔断: 1 分钟内 5 次失败 → 熔断 30 秒

### 7.3 禁止 OPS 调用
- CI 扫描禁止出现 OPS 域名或 `/ops/` 路径

## 8. Football 只读连接 (FW-H06)

### 8.1 连接要求
- 第二个 engine，只有 SELECT 权限
- 写拦截器: 非 SELECT 语句 → 抛错

### 8.2 结构校验
- 启动时比对 schema 文件与目标库
- 缺列或类型不同 → 拒绝启动

### 8.3 替身表
- 开发/测试: 在 环境变量 `IMS_DB_URL` 指向的库 建替身表
- 生产: 指向 `shenyu-live`
- `live_name LIKE '[STUB]%'` 标记测试数据

## 9. 错误码规范

### 9.1 域号段
| 域 | 号段 |
|---|---|
| COMMON | 1001, 1008, 1500-1504, 5001-5007 |
| AUTH | 1001-1010 |
| SYS | 1211-1220, 1281-1290 |
| FLOW | 1131-1140 |
| TRAIN | 1101-1120 |
| LIVE | 1271-1280 |

### 9.2 消息规范
- 中文消息，禁止含英文枚举码或 API 路径
- 静态检查: 出现 `[A-Z_]{3,}` 或 `/admin-api` → 失败

## 10. 性能约束

### 10.1 分页查询
- 部门树 (2000 部门, 2 万用户): ≤ 500ms

### 10.2 缓存策略
- 字典缓存: Redis `ims:dict:<type>`，本地 60 秒 TTL
- 权限缓存: Redis `ims:perm:<userId>:<version>`，30 分钟 TTL

## 11. 安全约束

### 11.1 敏感字段
- 手机号: AES 加密存储 (`mobile_enc`) + HMAC 哈希 (`mobile_hash`)
- 密码: bcrypt 哈希
- API Key: 加密存储，脱敏显示 `******`

### 11.2 日志安全
- 禁止输出密钥、连接串、堆栈
- 敏感字段脱敏: `password`, `secret`, `apiKey`, `token`

## 12. 静态检查项

以下模式出现在业务代码中将导致 CI 失败：

1. `datetime.now()` → 使用 `get_now()`
2. `tenant_id ==` 在业务代码中 → 使用框架自动过滤
3. 角色名判断 (`"R1"`, `role_key`, `in roles`)
4. `create_all(`, `ALTER TABLE` 在非迁移代码中
5. Football 表名在 `app/integrations/football_live/` 外
6. OPS 域名或 `/ops/` 路径
7. 路由层直接 `commit`
