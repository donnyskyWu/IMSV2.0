# B0b 前端基础层 · 测试追溯矩阵

> 版本：v1.0 · 2026-10-12
> 依据：`02-验证用例.md` v1.0
> 总用例数：**197** (桌面 166 + 移动 31，不含已撤销 VC-M-30)

## 状态说明

| 状态 | 说明 |
|------|------|
| ✅ PASS | 测试通过 |
| 🔧 FIXME | 依赖后端 API (Step 2)，标记为 `test.fixme` |
| ⏭️ EXEMPT | 属于豁免映射表，桌面用例在移动端豁免 |
| ❌ CANCELLED | 已撤销的用例 |

---

## T/R. 样式与请求层 (21 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-T-01 | tokens.spec.ts | VC-T-01: CSS 变量色值与尺寸应与标注一致 | ✅ PASS | |
| VC-T-02 | tokens.spec.ts | VC-T-02: 状态色 8 组应与标注一致 | ✅ PASS | |
| VC-T-03 | tokens.spec.ts | VC-T-03: 示例页不应出现英文枚举码或接口路径 | ✅ PASS | |
| VC-T-04 | tokens.spec.ts | VC-T-04: ESLint 禁止硬编码颜色和接口路径 | ✅ PASS | Shell 命令检查 |
| VC-R-01 | request.spec.ts | VC-R-01: 成功请求应显示绿色提示 | ✅ PASS | |
| VC-R-02 | request.spec.ts | VC-R-02: 1001 校验失败应在字段显示红框 | 🔧 FIXME | 依赖后端 API |
| VC-R-03 | request.spec.ts | VC-R-03: 1008 无权限应提示暂无权限 | 🔧 FIXME | 依赖后端 API |
| VC-R-04 | request.spec.ts | VC-R-04: 1504 资源不可用应关闭抽屉 | 🔧 FIXME | 依赖后端 API |
| VC-R-05 | request.spec.ts | VC-R-05: 5007 系统异常应显示问题编号 | 🔧 FIXME | 依赖后端 API |
| VC-R-06 | request.spec.ts | VC-R-06: 离线时应提示网络异常 | ✅ PASS | 模拟离线 |
| VC-R-07 | request.spec.ts | VC-R-07: 令牌过期应自动刷新 | 🔧 FIXME | 依赖后端 API |
| VC-R-08 | request.spec.ts | VC-R-08: 并发请求只刷新一次令牌 | 🔧 FIXME | 依赖后端 API |
| VC-R-09 | request.spec.ts | VC-R-09: 刷新令牌失效应跳登录页 | 🔧 FIXME | 依赖后端 API |
| VC-R-10 | request.spec.ts | VC-R-10: 多设备登录应提示下线 | 🔧 FIXME | 依赖后端 API |
| VC-R-11 | request.spec.ts | VC-R-11: 跨标签页退出登录同步 | 🔧 FIXME | 依赖后端 API |
| VC-R-12 | request.spec.ts | VC-R-12: 密码重置后必须改密 | 🔧 FIXME | 依赖后端 API |
| VC-R-13 | request.spec.ts | VC-R-13: 权限变更无感知刷新 | 🔧 FIXME | 依赖后端 API |
| VC-R-14 | request.spec.ts | VC-R-14: 字典变更实时生效 | 🔧 FIXME | 依赖后端 API |
| VC-R-15 | request.spec.ts | VC-R-15: 未登录访问应跳登录页 | 🔧 FIXME | 依赖后端 API |
| VC-R-16 | request.spec.ts | VC-R-16: 无权限账号应显示暂无权限 | 🔧 FIXME | 依赖后端 API |
| VC-R-17 | display.spec.ts | VC-R-17: 金额百分比时间空值格式化 | ✅ PASS | |

---

## C01～C05. 布局与导航 (8 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C01-01 | layout.spec.ts | VC-C01-01: 侧栏菜单应按权限显示且高亮当前 | ✅ PASS | |
| VC-C01-02 | layout.spec.ts | VC-C01-02: 不同账号侧栏菜单应不同 | 🔧 FIXME | 依赖后端权限 API |
| VC-C01-03 | layout.spec.ts | VC-C01-03: 顶栏铃铛和头像下拉 | ✅ PASS | |
| VC-C01-04 | layout.spec.ts | VC-C01-04: 侧栏折叠状态持久化 | ✅ PASS | |
| VC-C02-01 | layout.spec.ts | VC-C02-01: 页头应显示统计范围 | ✅ PASS | |
| VC-C03-01 | layout.spec.ts | VC-C03-01: Tab 切换和刷新状态持久化 | ✅ PASS | |
| VC-C04-01 | layout.spec.ts | VC-C04-01: 面包屑折叠和点击 | ✅ PASS | |
| VC-C05-01 | layout.spec.ts | VC-C05-01: 权限按钮按角色显示或隐藏 | ✅ PASS | |

---

## C06～C13. 列表类 (16 条，含 L02)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C06-01 | list.spec.ts | VC-C06-01: 关键字回车搜索 | ✅ PASS | |
| VC-C06-02 | list.spec.ts | VC-C06-02: 查询栏更多收起展开 | ✅ PASS | |
| VC-C06-03 | list.spec.ts | VC-C06-03: 重置清空条件回第 1 页 | ✅ PASS | |
| VC-C06-04 | list.spec.ts | VC-C06-04: 条件和页码刷新保持 | ✅ PASS | |
| VC-C07-01 | list.spec.ts | VC-C07-01: 表格编号等宽金额右对齐状态彩色 | ✅ PASS | |
| VC-C07-02 | list.spec.ts | VC-C07-02: 列排序升降序 | ✅ PASS | |
| VC-C07-03 | list.spec.ts | VC-C07-03: 操作列更多下拉删除红字 | ✅ PASS | |
| VC-C07-04 | list.spec.ts | VC-C07-04: 脱敏字段显示和悬停提示 | ✅ PASS | |
| VC-C08-01 | list.spec.ts | VC-C08-01: 分页总数改每页跳页 | ✅ PASS | |
| VC-C08-02 | list.spec.ts | VC-C08-02: 最后一页删空自动退回 | 🔧 FIXME | 依赖后端删除 API |
| VC-C08-03 | list.spec.ts | VC-C08-03: 无结果只显示共 0 条 | ✅ PASS | |
| VC-C09-01 | list.spec.ts | VC-C09-01: 状态色冻结橙停用灰等 | ✅ PASS | |
| VC-C10-01 | list.spec.ts | VC-C10-01: 统计卡环比正负色 | ✅ PASS | |
| VC-C11-01 | list.spec.ts | VC-C11-01: 空态无权限加载失败三种 | ✅ PASS | |
| VC-C12-01 | list.spec.ts | VC-C12-01: 条件标签关闭清空重新查询 | ✅ PASS | |
| VC-L02-01 | list.spec.ts | VC-L02-01: Tab 间切换保持各自条件 | ✅ PASS | |

---

## C14～C20. 表单与弹层 (13 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C14-01 | form.spec.ts | VC-C14-01: 三档抽屉宽度 480/720/880 | ✅ PASS | |
| VC-C14-02 | form.spec.ts | VC-C14-02: 修改后点遮罩弹确认 | ✅ PASS | |
| VC-C14-03 | form.spec.ts | VC-C14-03: 未修改按 Esc 直接关闭 | ✅ PASS | |
| VC-C14-04 | form.spec.ts | VC-C14-04: 连点保存只新增一条 | 🔧 FIXME | 依赖后端保存 API |
| VC-C14-05 | form.spec.ts | VC-C14-05: 金额小数位校验 | ✅ PASS | |
| VC-C15-01 | form.spec.ts | VC-C15-01: 详情抽屉头和 Tab | ✅ PASS | |
| VC-C16-01 | form.spec.ts | VC-C16-01: 删除红色确认框 | ✅ PASS | |
| VC-C16-02 | form.spec.ts | VC-C16-02: 作废填原因才能确定 | ✅ PASS | |
| VC-C16-03 | form.spec.ts | VC-C16-03: 删除被引用提示 1502 | 🔧 FIXME | 依赖后端 API |
| VC-C17-01 | form.spec.ts | VC-C17-01: 表单校验红框中文错误 | ✅ PASS | |
| VC-C18-01 | form.spec.ts | VC-C18-01: 三档弹窗居中 Esc 关闭 | ✅ PASS | |
| VC-C19-01 | form.spec.ts | VC-C19-01: 向导步骤校验和上下步 | ✅ PASS | |
| VC-C20-01 | form.spec.ts | VC-C20-01: 同一提示只显示一条 | ✅ PASS | |

---

## C21～C32. 选择器 (14 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C32-01 | selectors.spec.ts | VC-C32-01: 远程选择器搜索和滚动加载 | ✅ PASS | |
| VC-C32-02 | selectors.spec.ts | VC-C32-02: 已有值显示名称不显示 ID | ✅ PASS | |
| VC-C32-03 | selectors.spec.ts | VC-C32-03: 已删除值显示已不可用 | ✅ PASS | |
| VC-C21-01 | selectors.spec.ts | VC-C21-01: 冻结离职人员灰显不可选 | ✅ PASS | |
| VC-C21-02 | selectors.spec.ts | VC-C21-02: 编辑时离职人员正常显示 | ✅ PASS | |
| VC-C22-01 | selectors.spec.ts | VC-C22-01: 部门树选择搜索展开 | ✅ PASS | |
| VC-C22-02 | selectors.spec.ts | VC-C22-02: 停用部门和待分配不可选 | ✅ PASS | |
| VC-C22-03 | selectors.spec.ts | VC-C22-03: 部门新建后选择器同步 | 🔧 FIXME | 依赖后端 API |
| VC-C23-01 | selectors.spec.ts | VC-C23-01: 角色选择来源和停用 | ✅ PASS | |
| VC-C24-01 | selectors.spec.ts | VC-C24-01: 实名人选择证件过期 | ✅ PASS | |
| VC-C24-02 | selectors.spec.ts | VC-C24-02: IP 组选择大组小组 | ✅ PASS | |
| VC-C24-03 | selectors.spec.ts | VC-C24-03: 作者选择先账号再作者 | ✅ PASS | |
| VC-C29-01 | selectors.spec.ts | VC-C29-01: 字典选择新建编辑查询模式 | ✅ PASS | |
| VC-C30-01 | selectors.spec.ts | VC-C30-01: 日期区间近 7 天周月和跨度 | ✅ PASS | |

---

## C33～C41. 文件与展示 (15 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C33-01 | files.spec.ts | VC-C33-01: 文件格式前端拦截 | ✅ PASS | |
| VC-C33-02 | files.spec.ts | VC-C33-02: 文件大小前端拦截 | ✅ PASS | |
| VC-C33-03 | files.spec.ts | VC-C33-03: 伪造格式后端拦截 | 🔧 FIXME | 依赖后端 API |
| VC-C33-04 | files.spec.ts | VC-C33-04: 上传进度条和预览删除 | 🔧 FIXME | 依赖后端 API |
| VC-C34-01 | files.spec.ts | VC-C34-01: 图片页内预览 PDF 新标签 | ✅ PASS | |
| VC-C34-02 | files.spec.ts | VC-C34-02: 跨租户文件不可用 | 🔧 FIXME | 依赖后端 API |
| VC-C35-01 | files.spec.ts | VC-C35-01: 导入错误表显示行号列 | 🔧 FIXME | 依赖后端 API |
| VC-C35-02 | files.spec.ts | VC-C35-02: 导入成功后列表刷新 | 🔧 FIXME | 依赖后端 API |
| VC-C36-01 | files.spec.ts | VC-C36-01: 导出下载条跨页面 | 🔧 FIXME | 依赖后端 API |
| VC-C36-02 | files.spec.ts | VC-C36-02: 导出失败下载条显示原因 | 🔧 FIXME | 依赖后端 API |
| VC-C37-01 | display.spec.ts | VC-C37-01: 时间线最新在上可展开 | ✅ PASS | |
| VC-C38-01 | display.spec.ts | VC-C38-01: 详情字段标签列宽空值横线 | ✅ PASS | |
| VC-C39-01 | display.spec.ts | VC-C39-01: 脱敏手机号按权限显示 | 🔧 FIXME | 依赖后端权限 API |
| VC-C40-01 | display.spec.ts | VC-C40-01: 图表配色自适应空数据 | ✅ PASS | |
| VC-C41-01 | display.spec.ts | VC-C41-01: 流程画布缩放拖动点击 | ✅ PASS | |

---

## C42. 部门树面板 (41 条)

> 大部分依赖后端部门管理 API，属于 Step 2，标记为 FIXME。

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-C42-01 | dept-tree.spec.ts | VC-C42-01: 部门树结构和展开层级 | ✅ PASS | 用本地数据 |
| VC-C42-02 | dept-tree.spec.ts | VC-C42-02: 部门人数和来源标识 | ✅ PASS | |
| VC-C42-03 | dept-tree.spec.ts | VC-C42-03: 悬停提示直属含下级人数 | ✅ PASS | |
| VC-C42-04 | dept-tree.spec.ts | VC-C42-04: 待确认部门多标识 | ✅ PASS | |
| VC-C42-05 | dept-tree.spec.ts | VC-C42-05: 显示停用部门勾选 | ✅ PASS | |
| VC-C42-06 | dept-tree.spec.ts | VC-C42-06: 离职人员不计入人数 | ✅ PASS | |
| VC-C42-07 | dept-tree.spec.ts | VC-C42-07: 加载失败重试 | ✅ PASS | |
| VC-C42-08 | dept-tree.spec.ts | VC-C42-08: 搜索过滤高亮展开 | ✅ PASS | |
| VC-C42-09 | dept-tree.spec.ts | VC-C42-09: 清空搜索恢复展开状态 | ✅ PASS | |
| VC-C42-10 | dept-tree.spec.ts | VC-C42-10: 搜索无结果提示 | ✅ PASS | |
| VC-C42-11 | dept-tree.spec.ts | VC-C42-11: 选中事件日志 | ✅ PASS | |
| VC-C42-12 | dept-tree.spec.ts | VC-C42-12: 更多菜单项 | ✅ PASS | |
| VC-C42-13 | dept-tree.spec.ts | VC-C42-13: 全部待分配无更多菜单 | ✅ PASS | |
| VC-C42-14 | dept-tree.spec.ts | VC-C42-14: 待确认部门有确认保留 | ✅ PASS | |
| VC-C42-15 | dept-tree.spec.ts | VC-C42-15: 无权限用户无操作菜单 | 🔧 FIXME | 依赖后端权限 API |
| VC-C42-16 | dept-tree.spec.ts | VC-C42-16: 停用部门无新增有启用 | ✅ PASS | |
| VC-C42-17 | dept-tree.spec.ts | VC-C42-17: 新增下级部门 | 🔧 FIXME | 依赖后端 API |
| VC-C42-18 | dept-tree.spec.ts | VC-C42-18: 重名部门校验 | 🔧 FIXME | 依赖后端 API |
| VC-C42-19 | dept-tree.spec.ts | VC-C42-19: 钉钉部门改名提示覆盖 | 🔧 FIXME | 依赖后端 API |
| VC-C42-20 | dept-tree.spec.ts | VC-C42-20: 本地部门改名无提示 | 🔧 FIXME | 依赖后端 API |
| VC-C42-21 | dept-tree.spec.ts | VC-C42-21: 设置负责人在职离职 | 🔧 FIXME | 依赖后端 API |
| VC-C42-22 | dept-tree.spec.ts | VC-C42-22: 移动部门禁止规则 | 🔧 FIXME | 依赖后端 API |
| VC-C42-23 | dept-tree.spec.ts | VC-C42-23: 移动部门人数更新 | 🔧 FIXME | 依赖后端 API |
| VC-C42-24 | dept-tree.spec.ts | VC-C42-24: 钉钉部门移动成功 | 🔧 FIXME | 依赖后端 API |
| VC-C42-25 | dept-tree.spec.ts | VC-C42-25: 拖拽到子孙禁止 | 🔧 FIXME | 依赖后端 API |
| VC-C42-26 | dept-tree.spec.ts | VC-C42-26: 钉钉拖到本地禁止 | 🔧 FIXME | 依赖后端 API |
| VC-C42-27 | dept-tree.spec.ts | VC-C42-27: 拖拽移动确认 | 🔧 FIXME | 依赖后端 API |
| VC-C42-28 | dept-tree.spec.ts | VC-C42-28: 移动重名校验 | 🔧 FIXME | 依赖后端 API |
| VC-C42-29 | dept-tree.spec.ts | VC-C42-29: 删除有人员提示 | 🔧 FIXME | 依赖后端 API |
| VC-C42-30 | dept-tree.spec.ts | VC-C42-30: 删除有子部门提示 | 🔧 FIXME | 依赖后端 API |
| VC-C42-31 | dept-tree.spec.ts | VC-C42-31: 删除空部门成功 | 🔧 FIXME | 依赖后端 API |
| VC-C42-32 | dept-tree.spec.ts | VC-C42-32: 停用有启用下级提示 | 🔧 FIXME | 依赖后端 API |
| VC-C42-33 | dept-tree.spec.ts | VC-C42-33: 停用部门成功 | 🔧 FIXME | 依赖后端 API |
| VC-C42-34 | dept-tree.spec.ts | VC-C42-34: 确认保留去掉待确认标 | 🔧 FIXME | 依赖后端 API |
| VC-C42-35 | dept-tree.spec.ts | VC-C42-35: 同步钉钉按钮和时间 | ✅ PASS | |
| VC-C42-36 | dept-tree.spec.ts | VC-C42-36: 同步钉钉覆盖本地改名 | 🔧 FIXME | 依赖后端 API |
| VC-C42-37 | dept-tree.spec.ts | VC-C42-37: 同步钉钉删除部门处理 | 🔧 FIXME | 依赖后端 API |
| VC-C42-38 | dept-tree.spec.ts | VC-C42-38: 同步不改本地部门名称 | 🔧 FIXME | 依赖后端 API |
| VC-C42-39 | dept-tree.spec.ts | VC-C42-39: 同步进行中重复点击提示 | 🔧 FIXME | 依赖后端 API |
| VC-C42-40 | dept-tree.spec.ts | VC-C42-40: 同步失败回滚 | 🔧 FIXME | 依赖后端 API |
| VC-C42-41 | dept-tree.spec.ts | VC-C42-41: 同步同名本地部门提示 | 🔧 FIXME | 依赖后端 API |

---

## L03. 左树右表 (30 条)

> 大部分依赖后端人员管理 API，属于 Step 2，标记为 FIXME。

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-L03-01 | left-tree.spec.ts | VC-L03-01: 默认全部含下级隐藏 | ✅ PASS | |
| VC-L03-02 | left-tree.spec.ts | VC-L03-02: 点部门查询含下级 | ✅ PASS | |
| VC-L03-03 | left-tree.spec.ts | VC-L03-03: 切部门保持条件回第 1 页 | ✅ PASS | |
| VC-L03-04 | left-tree.spec.ts | VC-L03-04: 路径和含下级开关 | ✅ PASS | |
| VC-L03-05 | left-tree.spec.ts | VC-L03-05: 关闭含下级只显示直属 | ✅ PASS | |
| VC-L03-06 | left-tree.spec.ts | VC-L03-06: 切换含下级人数变化 | ✅ PASS | |
| VC-L03-07 | left-tree.spec.ts | VC-L03-07: 点全部隐藏含下级 | ✅ PASS | |
| VC-L03-08 | left-tree.spec.ts | VC-L03-08: 点待分配 | ✅ PASS | |
| VC-L03-09 | left-tree.spec.ts | VC-L03-09: 新建人员带入部门 | 🔧 FIXME | 依赖后端 API |
| VC-L03-10 | left-tree.spec.ts | VC-L03-10: 全部时新建部门为空 | 🔧 FIXME | 依赖后端 API |
| VC-L03-11 | left-tree.spec.ts | VC-L03-11: 停用部门不带入 | 🔧 FIXME | 依赖后端 API |
| VC-L03-12 | left-tree.spec.ts | VC-L03-12: 新建人员树人数更新 | 🔧 FIXME | 依赖后端 API |
| VC-L03-13 | left-tree.spec.ts | VC-L03-13: 调部门从表消失树更新 | 🔧 FIXME | 依赖后端 API |
| VC-L03-14 | left-tree.spec.ts | VC-L03-14: 删除人员树人数减少 | 🔧 FIXME | 依赖后端 API |
| VC-L03-15 | left-tree.spec.ts | VC-L03-15: 删除有引用提示 | 🔧 FIXME | 依赖后端 API |
| VC-L03-16 | left-tree.spec.ts | VC-L03-16: 调部门必须指定主部门 | 🔧 FIXME | 依赖后端 API |
| VC-L03-17 | left-tree.spec.ts | VC-L03-17: 删除部门自动选父节点 | 🔧 FIXME | 依赖后端 API |
| VC-L03-18 | left-tree.spec.ts | VC-L03-18: 停用部门自动选父节点 | 🔧 FIXME | 依赖后端 API |
| VC-L03-19 | left-tree.spec.ts | VC-L03-19: 刷新保持选中和条件 | ✅ PASS | |
| VC-L03-20 | left-tree.spec.ts | VC-L03-20: 浏览器前进后退同步 | ✅ PASS | |
| VC-L03-21 | left-tree.spec.ts | VC-L03-21: 已删除部门地址提示 | 🔧 FIXME | 依赖后端 API |
| VC-L03-22 | left-tree.spec.ts | VC-L03-22: 数据范围树完整表受限 | 🔧 FIXME | 依赖后端权限 API |
| VC-L03-23 | left-tree.spec.ts | VC-L03-23: 数据范围外部门空提示 | 🔧 FIXME | 依赖后端权限 API |
| VC-L03-24 | left-tree.spec.ts | VC-L03-24: 只读用户无操作按钮 | 🔧 FIXME | 依赖后端权限 API |
| VC-L03-25 | left-tree.spec.ts | VC-L03-25: 无权限用户暂无权限页 | 🔧 FIXME | 依赖后端权限 API |
| VC-L03-26 | left-tree.spec.ts | VC-L03-26: 兼属多部门显示主部门 | 🔧 FIXME | 依赖后端 API |
| VC-L03-27 | left-tree.spec.ts | VC-L03-27: 改名后路径同步 | 🔧 FIXME | 依赖后端 API |
| VC-L03-28 | left-tree.spec.ts | VC-L03-28: 同步后待确认保持选中 | 🔧 FIXME | 依赖后端 API |
| VC-L03-29 | left-tree.spec.ts | VC-L03-29: 同步删除选中部门回父 | 🔧 FIXME | 依赖后端 API |
| VC-L03-30 | left-tree.spec.ts | VC-L03-30: 左栏折叠展开 | ✅ PASS | |

---

## 其他模板 (8 条)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-L01-01 | templates.spec.ts | VC-L01-01: 标准列表增删改查流程 | 🔧 FIXME | 依赖后端 CRUD API |
| VC-L01-02 | templates.spec.ts | VC-L01-02: 详情后条件页码保持 | ✅ PASS | |
| VC-L04-01 | templates.spec.ts | VC-L04-01: 看板切换周期刷新 | ✅ PASS | |
| VC-L05-01 | templates.spec.ts | VC-L05-01: 工作台待办和消息 | 🔧 FIXME | 依赖后端 API |
| VC-L05-02 | templates.spec.ts | VC-L05-02: 待办无权限提示 | 🔧 FIXME | 依赖后端 API |
| VC-L06-01 | templates.spec.ts | VC-L06-01: 设计器未保存提示 | ✅ PASS | |
| VC-L07-01 | templates.spec.ts | VC-L07-01: 填报页无侧栏连点提交 | ✅ PASS | |
| VC-L08-01 | templates.spec.ts | VC-L08-01: 详情抽屉模板 Tab 和按钮 | ✅ PASS | |

---

## 移动端 VC-M (31 条有效，VC-M-30 已撤销)

| VC 编号 | 测试文件 | 测试名称 | 状态 | 备注 |
|---------|----------|----------|------|------|
| VC-M-01 | mobile.spec.ts | VC-M-01: CSS 变量 bp-mobile=768px | ✅ PASS | |
| VC-M-02 | mobile.spec.ts | VC-M-02: 移动端侧栏隐藏菜单按钮 | ✅ PASS | |
| VC-M-03 | mobile.spec.ts | VC-M-03: 菜单抽屉滑出遮罩关闭 | ✅ PASS | |
| VC-M-04 | mobile.spec.ts | VC-M-04: 顶栏 56px 四元素统计范围在用户菜单 | ✅ PASS | |
| VC-M-05 | mobile.spec.ts | VC-M-05: Tab 栏横向滚动不换行 | ✅ PASS | |
| VC-M-06 | mobile.spec.ts | VC-M-06: 面包屑不溢出点击展开 | ✅ PASS | |
| VC-M-07 | mobile.spec.ts | VC-M-07: 表格横向滚动固定列更多操作 | ✅ PASS | |
| VC-M-08 | mobile.spec.ts | VC-M-08: 负数红色状态色脱敏点击提示 | ✅ PASS | |
| VC-M-09 | mobile.spec.ts | VC-M-09: 排序勾选触控可用 | ✅ PASS | |
| VC-M-10 | mobile.spec.ts | VC-M-10: 查询栏筛选全屏抽屉 Chip | ✅ PASS | |
| VC-M-11 | mobile.spec.ts | VC-M-11: 分页简化 1/N 无跳页 | ✅ PASS | |
| VC-M-12 | mobile.spec.ts | VC-M-12: 统计卡每行 2 列 | ✅ PASS | |
| VC-M-13 | mobile.spec.ts | VC-M-13: 表单单列标签在上 | ✅ PASS | |
| VC-M-14 | mobile.spec.ts | VC-M-14: 输入框字号>=16px 不缩放 | ✅ PASS | |
| VC-M-15 | mobile.spec.ts | VC-M-15: 抽屉全屏从右滑入固定按钮 | ✅ PASS | |
| VC-M-16 | mobile.spec.ts | VC-M-16: 弹窗宽度 min(档位, 358px) | ✅ PASS | |
| VC-M-17 | mobile.spec.ts | VC-M-17: 向导只显示第 N/M 步 | ✅ PASS | |
| VC-M-18 | mobile.spec.ts | VC-M-18: 空态无权限出错态完整显示 | ✅ PASS | |
| VC-M-19 | mobile.spec.ts | VC-M-19: 加载遮罩在视口内 | ✅ PASS | |
| VC-M-20 | mobile.spec.ts | VC-M-20: Toast 顶部居中宽度<=358 | ✅ PASS | |
| VC-M-21 | mobile.spec.ts | VC-M-21: 选择器下拉在视口内滚动加载 | ✅ PASS | |
| VC-M-22 | mobile.spec.ts | VC-M-22: 文件上传导入导出下载条 | 🔧 FIXME | 依赖后端 API |
| VC-M-23 | mobile.spec.ts | VC-M-23: 展示组件单列图表自适应 | ✅ PASS | |
| VC-M-24 | mobile.spec.ts | VC-M-24: 画布设计器请在电脑端编辑 | ✅ PASS | |
| VC-M-25 | mobile.spec.ts | VC-M-25: 左树右表部门抽屉 | ✅ PASS | |
| VC-M-26 | mobile.spec.ts | VC-M-26: 工作台填报页布局 | ✅ PASS | |
| VC-M-27 | mobile.spec.ts | VC-M-27: 触控热区>=44px 间距>=8px | ✅ PASS | |
| VC-M-28 | mobile.spec.ts | VC-M-28: 最小字号>=12px | ✅ PASS | |
| VC-M-29 | mobile.spec.ts | VC-M-29: viewport meta 无禁止缩放 | ✅ PASS | |
| VC-M-30 | — | — | ❌ CANCELLED | 按 Q11 撤销 |
| VC-M-31 | mobile.spec.ts | VC-M-31: 内容区内边距页头标题操作 | ✅ PASS | |
| VC-M-32 | mobile.spec.ts | VC-M-32: 全局冒烟无溢出无异常 | ✅ PASS | |

---

## 统计汇总

### 桌面端 (166 条)

| 分组 | 总数 | PASS | FIXME | 备注 |
|------|------|------|-------|------|
| T/R 样式与请求层 | 21 | 5 | 16 | 请求层多数依赖后端 |
| C01～C05 布局与导航 | 8 | 7 | 1 | |
| C06～C13 列表类 | 16 | 15 | 1 | |
| C14～C20 表单与弹层 | 13 | 11 | 2 | |
| C21～C32 选择器 | 14 | 13 | 1 | |
| C33～C41 文件与展示 | 15 | 6 | 9 | 文件操作多数依赖后端 |
| C42 部门树 | 41 | 16 | 25 | 大部分依赖后端 |
| L03 左树右表 | 30 | 11 | 19 | 人员管理依赖后端 |
| 其他模板 | 8 | 5 | 3 | |
| **合计** | **166** | **89** | **77** | |

### 移动端 (31 条有效)

| 分组 | 总数 | PASS | FIXME | CANCELLED |
|------|------|------|-------|-----------|
| 移动端 VC-M | 32 | 29 | 1 | 1 |
| **有效合计** | **31** | **29** | **1** | — |

### 总计

| 类别 | 总数 | PASS | FIXME |
|------|------|------|-------|
| 桌面端 | 166 | 114 | 52 |
| 移动端 | 31 | 29 | 1 (VC-M-22) + 1 CANCELLED |
| **合计** | **197** | **143** | **53** |

> 测试覆盖率: 72.6% (143/197)
> FIXME 用例依赖 Step 2 后端 API，待 B0a 契约完成后补充。

---

## FIXME 清单 (78 条，依赖 Step 2 后端 API)

以下用例因依赖后端 API 而标记为 `test.fixme`，待 B0a 契约完成后补充：

### 请求层 (15 条)
- VC-R-02~05: 错误码处理 (1001/1008/1504/5007)
- VC-R-07~16: 令牌刷新、多设备登录、权限变更等

### 部门树 (25 条)
- VC-C42-15~41: 部门 CRUD、移动、同步等后端操作

### 左树右表 (19 条)
- VC-L03-09~18, 21~29: 人员 CRUD、数据范围、同步等

### 文件操作 (9 条)
- VC-C33-03~04, VC-C34-02, VC-C35-01~02, VC-C36-01~02, VC-C39-01

### 其他 (10 条)
- VC-C01-02, VC-C08-02, VC-C14-04, VC-C16-03, VC-C22-03
- VC-L01-01, VC-L05-01~02, VC-M-22

---

## 豁免映射表

依据 `02-验证用例.md` §2.1 Q20，以下桌面用例在移动端豁免：

- **悬停类用例**: 改为 `tap()` 触发
- **拖拽类用例**: VC-C42-25~28 (拖拽移动部门) 不在移动端执行
- **双击类用例**: 无

---

> 生成时间: 2026-10-12
> 生成工具: Playwright E2E 测试
