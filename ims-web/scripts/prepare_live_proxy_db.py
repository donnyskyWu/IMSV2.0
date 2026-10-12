#!/usr/bin/env python3
"""为 Vite 代理联通用例准备数据库。版本：2026-10-12。

做的事：
- 按当前模型建表
- 执行仓库已有 tools.seed（租户、字典、参数、菜单、R1–R11、部门）
- 写入可登录账号 qa_admin（密码默认 Test1234）并挂上已有 R1

不做的事（留给小白 fix(B0)，缺了则 /me 菜单为空）：
- 不补租户套餐
- 不补套餐菜单
- 不补 R1 角色-菜单

环境变量：IMS_ENV、IMS_DB_URL、IMS_JWT_SECRET；可选 E2E_SEED_USERNAME、E2E_SEED_PASSWORD。
"""

from __future__ import annotations

import os
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
    import bcrypt

    import app.db.session as db_session
    from app.db.base import Base
    from app.domains.shared import models as _shared_models  # noqa: F401
    from app.domains.sys import models as _sys_models  # noqa: F401
    from app.domains.sys.models import Role, User, UserRole
    from tools.seed.runner import run_seeds

    # init_db 会改模块级 engine，不能用 from import 拿到的旧引用
    db_session.init_db()
    engine = db_session.engine
    session_factory = db_session.SessionLocal
    if engine is None or session_factory is None:
        raise SystemExit("数据库引擎未初始化")

    # 联通用例只需要和当前模型一致的表，不改迁移脚本
    Base.metadata.create_all(bind=engine)

    session = session_factory()
    token = db_session._db_session.set(session)
    try:
        if not run_seeds(os.environ.get("IMS_ENV", "dev")):
            raise SystemExit("tools.seed 执行失败")

        username = os.environ.get("E2E_SEED_USERNAME", "qa_admin")
        password = os.environ.get("E2E_SEED_PASSWORD", "Test1234")
        role = session.query(Role).filter(
            Role.tenant_id == 1,
            Role.role_key == "R1",
            Role.deleted == 0,
        ).first()
        if role is None:
            raise SystemExit("种子里没有 R1，无法挂登录账号")

        user = session.query(User).filter(
            User.tenant_id == 1,
            User.username == username,
            User.deleted == 0,
        ).first()
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        if user is None:
            user = User(
                tenant_id=1,
                username=username,
                nickname="测试-组织管理员",
                password_hash=password_hash,
                status="ACTIVE",
                source="LOCAL",
                pwd_reset_required=False,
            )
            session.add(user)
            session.flush()
        else:
            # 同一库重复准备时，保证用例使用的密码仍然能登录
            user.password_hash = password_hash
            user.status = "ACTIVE"
            user.pwd_reset_required = False
            session.flush()

        link = session.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        ).first()
        if link is None:
            session.add(UserRole(
                tenant_id=1,
                user_id=user.id,
                role_id=role.id,
                source="MANUAL",
                manual_removed=False,
            ))
        session.commit()
        print(f"live-proxy seed user ready: {username} role=R1")
    finally:
        db_session._db_session.reset(token)
        session.close()


if __name__ == "__main__":
    main()
