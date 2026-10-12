"""默认套餐、R1 菜单授权和 e2e 账号的种子。

只断言 main 上已经存在的菜单，不要求 B1 权限码或 R2/R4/R10 授权。
"""

from app.domains.sys.models import (
    Menu,
    Role,
    RoleMenu,
    Tenant,
    TenantPackage,
    TenantPackageMenu,
    User,
)


def _perm_codes(db_session) -> set[str]:
    return {
        code
        for (code,) in db_session.query(Menu.perm_code).all()
        if code
    }


def test_package_and_r1_grants_are_idempotent(db_session):
    """补套餐和 R1 菜单；重复执行不覆盖管理员改过的套餐，也不给其他角色授权。"""
    from tools.seed.access import DEFAULT_PACKAGE_NAME, seed_access
    from tools.seed.menus import seed_menus
    from tools.seed.roles import seed_roles
    from tools.seed.tenant import seed_tenant

    assert seed_tenant(env="test") == 1
    assert seed_menus(env="test") > 0
    assert seed_roles(env="test") > 0

    before_codes = _perm_codes(db_session)
    menu_count = db_session.query(Menu).filter(Menu.deleted == 0).count()
    assert menu_count > 0

    inserted = seed_access(env="test")
    assert inserted == 1 + menu_count * 2

    package = db_session.query(TenantPackage).filter(
        TenantPackage.name == DEFAULT_PACKAGE_NAME,
        TenantPackage.deleted == 0,
    ).one()
    tenant = db_session.query(Tenant).filter(Tenant.id == 1).one()
    assert tenant.package_id == package.id
    assert db_session.query(TenantPackageMenu).filter(
        TenantPackageMenu.package_id == package.id,
    ).count() == menu_count

    r1 = db_session.query(Role).filter(Role.role_key == "R1", Role.deleted == 0).one()
    assert db_session.query(RoleMenu).filter(RoleMenu.role_id == r1.id).count() == menu_count

    for role_key in ("R2", "R4", "R10"):
        role = db_session.query(Role).filter(Role.role_key == role_key, Role.deleted == 0).one()
        assert db_session.query(RoleMenu).filter(RoleMenu.role_id == role.id).count() == 0

    # 不新增菜单，也不写入 B1 权限码。
    assert _perm_codes(db_session) == before_codes
    assert all(code.startswith("ims:system:") for code in before_codes)

    package.name = "已改名"
    package.status = "DISABLED"
    admin_package = TenantPackage(tenant_id=1, name="管理员套餐", status="ENABLED")
    db_session.add(admin_package)
    db_session.flush()
    tenant.package_id = admin_package.id
    db_session.commit()

    # 管理员套餐还没有菜单行，只补这一侧；R1 的角色菜单已经齐了。
    assert seed_access(env="test") == menu_count
    db_session.refresh(package)
    db_session.refresh(tenant)
    db_session.refresh(admin_package)
    assert package.name == "已改名"
    assert package.status == "DISABLED"
    assert tenant.package_id == admin_package.id
    assert db_session.query(TenantPackageMenu).filter(
        TenantPackageMenu.package_id == admin_package.id,
    ).count() == menu_count
    # 再跑一次没有任何新行。
    assert seed_access(env="test") == 0


def test_e2e_user_keeps_existing_password(db_session):
    """e2e 账号只在 e2e 环境创建，重复执行不覆盖密码。"""
    import bcrypt

    from tools.seed.roles import seed_roles
    from tools.seed.tenant import seed_tenant
    from tools.seed.users import E2E_PASSWORD, E2E_USERNAME, seed_users

    assert seed_users(env="test") == 0
    assert db_session.query(User).filter(User.username == E2E_USERNAME).first() is None

    seed_tenant(env="e2e")
    seed_roles(env="e2e")
    assert seed_users(env="e2e") == 2  # 用户 + R1 关联

    user = db_session.query(User).filter(User.username == E2E_USERNAME).one()
    assert user.nickname == "测试-管理员"
    assert user.status == "ACTIVE"
    assert bcrypt.checkpw(E2E_PASSWORD.encode(), user.password_hash.encode())

    replacement = bcrypt.hashpw(b"Other1234", bcrypt.gensalt(rounds=4)).decode()
    user.password_hash = replacement
    user.nickname = "管理员改过"
    db_session.commit()

    assert seed_users(env="e2e") == 0
    db_session.refresh(user)
    assert user.password_hash == replacement
    assert user.nickname == "管理员改过"
    assert bcrypt.checkpw(b"Other1234", user.password_hash.encode())
