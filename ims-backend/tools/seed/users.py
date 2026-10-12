"""E2E 登录账号。

只在 --env e2e 写入。密码 Test1234，bcrypt cost=10。
已存在的用户不改密码、姓名、状态或部门。

e2e_admin 是 PR #15 的集成测试账号，缺 R1 关联时补上。
02 §0.2 的 test_* 账号整行已存在则跳过，不补角色。
部门或租户还没种上时跳过对应 test_*，避免单独跑 users 把 e2e_admin 一起失败掉。

test_r10 只绑角色键 R10（种子显示名「外部协作」，规格称外协），对应 FP-B1-LG-10 / E2E-B1-LG-23。

钉钉成员、岗位规则、同步事件仍由提测脚本 tools/e2e_seed/b1.py 负责。
平台超级管理员：B0a 没有给出用户名，这里不另造生产账号。
"""

import bcrypt

from tools.seed.timeutil import seed_now

# 集成测试与本地 e2e 共用这一组账号。不要在 dev/test/prod 种子里创建。
E2E_USERNAME = "e2e_admin"
E2E_PASSWORD = "Test1234"
E2E_NICKNAME = "测试-管理员"

# role_key 为空表示不绑角色。tenant_id 默认 1。
E2E_ACCOUNTS = [
    {"username": "test_admin", "nickname": "测试管理员", "role_key": "R1", "dept": "信息部", "status": "ACTIVE"},
    {"username": "test_xz", "nickname": "测试行政", "role_key": "R2", "dept": "行政部", "status": "ACTIVE"},
    {"username": "test_yyzj", "nickname": "测试运营总监", "role_key": "R4", "dept": "运营中心", "status": "ACTIVE"},
    {"username": "test_yg", "nickname": "测试员工", "role_key": "e2e_live_ops", "dept": "市场一部", "status": "ACTIVE"},
    {"username": "test_scope", "nickname": "测试范围", "role_key": "e2e_dept_view", "dept": "市场一部", "status": "ACTIVE"},
    {"username": "test_norole", "nickname": "测试无角色", "role_key": None, "dept": "市场一部", "status": "ACTIVE"},
    {"username": "test_lock", "nickname": "测试锁定", "role_key": "e2e_live_ops", "dept": "市场一部", "status": "ACTIVE"},
    {"username": "test_frozen", "nickname": "测试冻结", "role_key": "e2e_live_ops", "dept": "市场一部", "status": "FROZEN"},
    {"username": "test_resigned", "nickname": "测试离职", "role_key": "e2e_live_ops", "dept": "市场一部", "status": "RESIGNED"},
    {
        "username": "test_reset",
        "nickname": "测试改密",
        "role_key": "e2e_live_ops",
        "dept": "市场一部",
        "status": "ACTIVE",
        "pwd_reset_required": True,
    },
    {
        "username": "test_t2",
        "nickname": "测试停用租户",
        "role_key": "R1",
        "dept": None,
        "status": "ACTIVE",
        "tenant_id": 2,
    },
    {
        "username": "test_r10",
        "nickname": "测试外协",
        "role_key": "R10",
        "dept": None,
        "status": "ACTIVE",
    },
]


def seed_users(env: str, dry_run: bool = False) -> int:
    """写入 e2e_admin 和 02 §0.2 账号。非 e2e 环境什么都不做。"""
    if env != "e2e":
        return 0
    if dry_run:
        print(f"  Would seed e2e user {E2E_USERNAME} and {len(E2E_ACCOUNTS)} scenario users")
        return 1 + len(E2E_ACCOUNTS)

    from app.db.session import get_db_session
    from app.domains.sys.models import Dept, Role, Tenant, User, UserDept, UserRole

    session = get_db_session()
    now = seed_now()
    # 同一密码只哈希一次，本文件列出的测试账号共用。
    password_hash = bcrypt.hashpw(
        E2E_PASSWORD.encode(), bcrypt.gensalt(rounds=10)
    ).decode()
    inserted = _seed_e2e_admin(session, now, password_hash, Role, User, UserRole)
    inserted += _seed_scenario_accounts(
        session, now, password_hash, Dept, Role, Tenant, User, UserDept, UserRole,
    )
    session.commit()
    return inserted


def _seed_e2e_admin(session, now, password_hash, role_cls, user_cls, user_role_cls) -> int:
    """PR #15：e2e_admin 不存在才建，已存在则只补缺失的 R1。"""
    role = session.query(role_cls).filter(
        role_cls.tenant_id == 1,
        role_cls.role_key == "R1",
        role_cls.deleted == 0,
    ).first()
    if role is None:
        raise RuntimeError("R1 role is missing; seed roles before e2e users")

    inserted = 0
    user = session.query(user_cls).filter(
        user_cls.tenant_id == 1,
        user_cls.username == E2E_USERNAME,
        user_cls.deleted == 0,
    ).first()
    if user is None:
        user = user_cls(
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

    link = session.query(user_role_cls).filter(
        user_role_cls.user_id == user.id,
        user_role_cls.role_id == role.id,
    ).first()
    if link is None:
        session.add(user_role_cls(
            tenant_id=1,
            user_id=user.id,
            role_id=role.id,
            source="MANUAL",
            creator=0,
            create_time=now,
        ))
        inserted += 1
    return inserted


def _seed_scenario_accounts(
    session, now, password_hash, dept_cls, role_cls, tenant_cls, user_cls, user_dept_cls, user_role_cls,
) -> int:
    """02 场景账号。整行已存在则跳过。依赖的部门或租户不在时也跳过。"""
    count = 0
    for account in E2E_ACCOUNTS:
        tenant_id = account.get("tenant_id", 1)
        existing = session.query(user_cls).filter(
            user_cls.tenant_id == tenant_id,
            user_cls.username == account["username"],
            user_cls.deleted == 0,
        ).first()
        if existing is not None:
            continue
        if not _tenant_ready(session, tenant_cls, tenant_id):
            continue
        dept = _resolve_dept(session, dept_cls, tenant_id, account.get("dept"))
        if account.get("dept") and dept is None:
            continue
        user = user_cls(
            tenant_id=tenant_id,
            username=account["username"],
            nickname=account["nickname"],
            password_hash=password_hash,
            status=account["status"],
            source="LOCAL",
            main_dept_id=dept.id if dept is not None else None,
            pwd_reset_required=bool(account.get("pwd_reset_required", False)),
            creator=0,
            create_time=now,
        )
        session.add(user)
        session.flush()
        if dept is not None:
            session.add(user_dept_cls(
                tenant_id=tenant_id,
                user_id=user.id,
                dept_id=dept.id,
                is_main=True,
                source="LOCAL",
                creator=0,
                create_time=now,
            ))
        role_key = account.get("role_key")
        if role_key:
            role = session.query(role_cls).filter(
                role_cls.tenant_id == tenant_id,
                role_cls.role_key == role_key,
                role_cls.deleted == 0,
            ).first()
            if role is None:
                raise RuntimeError(f"E2E 角色不存在: {role_key} tenant={tenant_id}")
            session.add(user_role_cls(
                tenant_id=tenant_id,
                user_id=user.id,
                role_id=role.id,
                source="MANUAL",
                creator=0,
                create_time=now,
            ))
        count += 1
    return count


def _tenant_ready(session, tenant_cls, tenant_id: int) -> bool:
    """租户 1 由前面的种子保证。其他租户不存在时不建它的测试账号。"""
    if tenant_id == 1:
        return True
    return session.query(tenant_cls).filter(
        tenant_cls.id == tenant_id,
        tenant_cls.deleted == 0,
    ).first() is not None


def _resolve_dept(session, dept_cls, tenant_id: int, name: str | None):
    """租户 2 用根部门。其他账号按部门名查找。找不到时返回 None。"""
    if tenant_id != 1:
        return session.query(dept_cls).filter(
            dept_cls.tenant_id == tenant_id,
            dept_cls.parent_id == 0,
            dept_cls.deleted == 0,
        ).first()
    if not name:
        return None
    return session.query(dept_cls).filter(
        dept_cls.tenant_id == tenant_id,
        dept_cls.name == name,
        dept_cls.deleted == 0,
    ).first()
