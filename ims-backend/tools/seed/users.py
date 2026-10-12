"""E2E 登录账号。

只在 ``--env e2e`` 写入。已存在的用户不改密码、不改姓名，只补缺失的 R1 关联。
"""

import bcrypt

from app.core.clock import get_now

# 集成测试与本地 e2e 共用这一组账号。不要在 dev/test/prod 种子里创建。
E2E_USERNAME = "e2e_admin"
E2E_PASSWORD = "Test1234"
E2E_NICKNAME = "测试-管理员"


def seed_users(env: str, dry_run: bool = False) -> int:
    """写入 e2e 登录用户并挂上 R1。非 e2e 环境什么都不做。"""
    if env != "e2e":
        return 0
    if dry_run:
        print(f"  Would seed e2e user {E2E_USERNAME}")
        return 1

    from app.db.session import get_db_session
    from app.domains.sys.models import Role, User, UserRole

    session = get_db_session()
    now = get_now()
    inserted = 0

    role = session.query(Role).filter(
        Role.tenant_id == 1,
        Role.role_key == "R1",
        Role.deleted == 0,
    ).first()
    if role is None:
        raise RuntimeError("R1 role is missing; seed roles before e2e users")

    user = session.query(User).filter(
        User.tenant_id == 1,
        User.username == E2E_USERNAME,
        User.deleted == 0,
    ).first()
    if user is None:
        # 只在第一次写入密码。之后重复执行不得覆盖管理员改过的口令。
        password_hash = bcrypt.hashpw(
            E2E_PASSWORD.encode(),
            bcrypt.gensalt(rounds=10),
        ).decode()
        user = User(
            tenant_id=1,
            username=E2E_USERNAME,
            nickname=E2E_NICKNAME,
            password_hash=password_hash,
            status="ACTIVE",
            source="LOCAL",
            pwd_reset_required=False,
            creator=0,
            create_time=now,
        )
        session.add(user)
        session.flush()
        inserted += 1

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
            creator=0,
            create_time=now,
        ))
        inserted += 1

    session.commit()
    return inserted
