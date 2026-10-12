#!/usr/bin/env python3
"""为 Vite 代理联通用例准备数据库。版本：2026-10-12。

做的事：
- 按当前模型建表
- 执行 ``python -m tools.seed --env e2e``
  （套餐、套餐菜单、R1 角色菜单、登录账号都由这套种子写入）

登录账号只存在 ``tools.seed.users`` 的 E2E_USERNAME / E2E_PASSWORD。
非 e2e 环境不会写入该账号。本脚本不另造用户、不另写密码。

环境变量：IMS_DB_URL、IMS_JWT_SECRET。API 进程保持 IMS_ENV=dev 即可。
种子子进程会把 IMS_ENV 设成 e2e；若没配 Redis，只补一个占位地址
（种子不连 Redis，与后端集成测试相同）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# 必须先放到后端目录并写好环境变量，再导入 app（配置在导入时读取）
BACKEND = Path(__file__).resolve().parents[2] / "ims-backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

os.environ.setdefault("IMS_ENV", "dev")
if not os.environ.get("IMS_DB_URL"):
    raise SystemExit("缺少 IMS_DB_URL")
os.environ.setdefault("IMS_JWT_SECRET", "test-jwt-secret-for-live-proxy")


def main() -> None:
    import app.db.session as db_session
    from app.db.base import Base
    from app.domains.shared import models as _shared_models  # noqa: F401
    from app.domains.sys import models as _sys_models  # noqa: F401
    from tools.seed.users import E2E_USERNAME

    # init_db 会改模块级 engine，不能用 from import 拿到的旧引用
    db_session.init_db()
    engine = db_session.engine
    if engine is None:
        raise SystemExit("数据库引擎未初始化")

    # 联通用例只需要和当前模型一致的表，不改迁移脚本
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    seed_env = os.environ.copy()
    # e2e 启动校验要求 redis.url 非空；种子本身不连 Redis。
    if not seed_env.get("IMS_REDIS_URL"):
        seed_env["IMS_REDIS_URL"] = "redis://127.0.0.1:6379/0"

    seeded = subprocess.run(
        [sys.executable, "-m", "tools.seed", "--env", "e2e"],
        cwd=BACKEND,
        env=seed_env,
        check=False,
    )
    if seeded.returncode != 0:
        raise SystemExit("python -m tools.seed --env e2e 失败")

    print(f"live-proxy seed user ready: {E2E_USERNAME}")


if __name__ == "__main__":
    main()
