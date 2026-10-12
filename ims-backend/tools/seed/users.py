"""测试登录账号。

test_admin 在 test 和 e2e 环境写入，密码 Test1234。dev、prod 不创建。
已存在的用户不改密码、姓名、状态或部门。test_admin 缺 R1 时补上。

02 §0.2 的其余 test_* 只在 e2e 写入。整行已存在则跳过，不补角色。
部门或租户还没种上时跳过对应账号。test_admin 没有「信息部」时仍创建，部门留空。

test_r10 只绑角色键 R10（种子显示名「外部协作」，规格称外协），对应 FP-B1-LG-10 / E2E-B1-LG-23。

钉钉成员、岗位规则、同步事件仍由提测脚本 tools/e2e_seed/b1.py 负责。
平台超级管理员：B0a 没有给出用户名，这里不另造生产账号。
"""

import bcrypt

from tools.seed.timeutil import seed_now

# 02 §0.2 的管理员账号。test 与 e2e 都能登录，prod 不创建。
E2E_USERNAME = "test_admin"
E2E_PASSWORD = "Test1234"
E2E_NICKNAME = "测试管理员"
LOGIN_ENVS = frozenset({"test", "e2e"})

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
    """写入 test_admin，以及 e2e 下的 02 §0.2 账号。dev / prod 什么都不做。"""
    accounts = _accounts_for(env)
    if not accounts:
        return 0
    if dry_run:
        print(f"  Would seed {len(accounts)} users, including {E2E_USERNAME}")
        return len(accounts)

    from app.db.session import get_db_session
    from app.domains.sys.models import Dept, Role, Tenant, User, UserDept, UserRole

    session = get_db_session()
    now = seed_now()
    # 同一密码只哈希一次，本文件列出的测试账号共用。
    password_hash = bcrypt.hashpw(
        E2E_PASSWORD.encode(), bcrypt.gensalt(rounds=10)
    ).decode()
    inserted = _seed_accounts(
        session, accounts, now, password_hash, Dept, Role, Tenant, User, UserDept, UserRole,
    )
    session.commit()
    return inserted


def _accounts_for(env: str) -> list[dict]:
    """test 只给登录账号。e2e 给 02 的全部场景账号。"""
    if env == "e2e":
        return E2E_ACCOUNTS
    if env == "test":
        return [row for row in E2E_ACCOUNTS if row["username"] == E2E_USERNAME]
    return []


def _seed_accounts(
    session, accounts, now, password_hash, dept_cls, role_cls, tenant_cls, user_cls, user_dept_cls, user_role_cls,
) -> int:
    """整行已存在则跳过。test_admin 例外：缺 R1 时补关联，仍不改密码和姓名。"""
    count = 0
    for account in accounts:
        tenant_id = account.get("tenant_id", 1)
        existing = session.query(user_cls).filter(
            user_cls.tenant_id == tenant_id,
            user_cls.username == account["username"],
            user_cls.deleted == 0,
        ).first()
        if existing is not None:
            if account["username"] == E2E_USERNAME:
                count += _ensure_role(
                    session, existing, account, now, role_cls, user_role_cls,
                )
            continue
        if not _tenant_ready(session, tenant_cls, tenant_id):
            continue
        dept = _resolve_dept(session, dept_cls, tenant_id, account.get("dept"))
        if account.get("dept") and dept is None and account["username"] != E2E_USERNAME:
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
        count += 1
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
        count += _ensure_role(session, user, account, now, role_cls, user_role_cls)
    return count


def _ensure_role(session, user, account, now, role_cls, user_role_cls) -> int:
    """角色不存在就报错。关联已在则不重复插入。"""
    role_key = account.get("role_key")
    if not role_key:
        return 0
    role = session.query(role_cls).filter(
        role_cls.tenant_id == user.tenant_id,
        role_cls.role_key == role_key,
        role_cls.deleted == 0,
    ).first()
    if role is None:
        raise RuntimeError(f"角色不存在: {role_key} tenant={user.tenant_id}")
    link = session.query(user_role_cls).filter(
        user_role_cls.user_id == user.id,
        user_role_cls.role_id == role.id,
    ).first()
    if link is not None:
        return 0
    session.add(user_role_cls(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role_id=role.id,
        source="MANUAL",
        creator=0,
        create_time=now,
    ))
    return 1


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
