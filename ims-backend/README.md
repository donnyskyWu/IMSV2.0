# IMS v2 后端

IMS（资源管理系统）v2.0 后端服务，基于 Python 3.11+ / FastAPI / SQLAlchemy 2.0 构建。

## 技术栈

- **Python 3.11+**: 运行时
- **FastAPI**: Web 框架
- **SQLAlchemy 2.0**: ORM
- **Alembic**: 数据库迁移
- **Redis**: 缓存与会话存储
- **MySQL 8**: 主数据库
- **pytest**: 测试框架

## 项目结构

```
ims-backend/
├── app/
│   ├── api/           # API 路由层
│   ├── core/          # 核心配置、上下文、错误码
│   ├── db/            # 数据库会话、基类、仓储
│   ├── domains/       # 按域分包的业务模型
│   │   └── sys/       # 系统管理域
│   ├── integrations/  # 外部系统适配器
│   ├── services/      # 业务逻辑服务层
│   └── worker/        # 定时任务入口
├── migrations/        # Alembic 迁移
├── tests/             # 测试代码
│   ├── unit/          # 单元测试
│   └── integration/   # 集成测试
├── tools/
│   ├── scaffold/      # 增删改查脚手架
│   └── football_stub/ # 替身表造数
└── pyproject.toml     # 项目配置
```

## 快速开始

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 环境变量

创建 `.env` 文件或设置环境变量：

```bash
IMS_ENV=dev
IMS_DB_URL=mysql+pymysql://user:pass@localhost:3306/imsV2.0
IMS_REDIS_URL=redis://localhost:6379/0
IMS_JWT_SECRET=your-secret-key
```

### 运行开发服务器

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 带覆盖率
pytest tests/ -v --cov=app --cov-report=term-missing
```

## API 文档

开发环境访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 关键技术约束

详见 [docs/engineering/TECH-CONSTRAINTS.md](../docs/engineering/TECH-CONSTRAINTS.md)

### 时间处理

```python
# 禁止
from datetime import datetime
now = datetime.now()

# 正确
from app.core.clock import get_now
now = get_now()
```

### 错误处理

```python
from app.core.errors import BizError

# 抛出业务错误
raise BizError(1001, msg="参数错误")
raise BizError.not_found()  # 1504
raise BizError.no_permission()  # 1008
```

### 事务管理

```python
from app.db.transaction import transactional

class MyService:
    @transactional
    def create_something(self, data):
        # 自动开启事务，异常自动回滚
        ...
```

### 权限控制

```python
from app.api.deps import require_permission, require_any_permission

@router.get("/users")
async def get_users(
    _: int = Depends(require_permission("ims:system:user:query"))
):
    ...
```

## 种子

先迁移再灌种子。连接串只放在环境变量 `IMS_DB_URL`，不要写进仓库。

```bash
alembic upgrade head
python -m tools.seed --env dev
# 02 §0.2 测试账号（密码 Test1234）只在 e2e 环境创建
python -m tools.seed --env e2e
```

重复执行只补缺：不改管理员已经改过的角色、菜单名称、字典标签、参数值；管理员删掉的默认授权不会被加回去。

## 数据库迁移

```bash
# 生成迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 代码规范

- 使用 `ruff` 进行代码检查
- 使用 `mypy` 进行类型检查

```bash
ruff check app/ tests/
mypy app/ --ignore-missing-imports
```

## 版本历史

- **2.0.0**: 初始版本，框架核心实现
- **B1-M01 PR1**: 种子与迁移基础（标准角色 R2=`DEPT`、B1 菜单授权、§0.5 加列）
