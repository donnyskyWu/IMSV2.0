"""真实数据库上的 HTTP 集成测试。

不使用 dependency_overrides，也不替换 get_db 或会话。
账号由 `python -m tools.seed --env e2e` 写入，密码 Test1234。
CI 使用 workflow 里的 MySQL；本机没配库时退回 IMS_DB_URL。

库里已经有种子时也要能抓住两件事：种子没把套餐授权写回去，
以及登录只 flush 不 commit。断言都走请求之外的新连接。
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _shared_url(tmp_path: Path) -> tuple[str, str]:
    """返回 (实际连接串, 调用前的 settings.db.url)。

    内存库无法跨进种子子进程，这种情况下改用同一个 sqlite 文件。
    CI 的 IMS_DB_URL 是 MySQL，不会走到这个分支。
    """
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.db.url
    if not original or ":memory:" in original:
        url = f"sqlite:///{tmp_path / 'ims-real.db'}"
        settings.db.url = url
        return url, original
    return original, original


def _connect(url: str):
    """打开一条与请求会话无关的连接。调用方负责关闭。"""
    engine = create_engine(url)
    session = sessionmaker(bind=engine)()
    return engine, session


def _strip_package_grants(url: str) -> None:
    """清掉套餐菜单、R1 角色菜单和租户套餐指针。

    已经种过的库如果不再跑 access 种子，这些行不会自己回来。
    """
    from app.domains.sys.models import Role, RoleMenu, Tenant, TenantPackageMenu

    engine, session = _connect(url)
    try:
        session.query(TenantPackageMenu).delete()
        role_ids = [
            row.id
            for row in session.query(Role).filter(Role.role_key == "R1", Role.deleted == 0)
        ]
        if role_ids:
            session.query(RoleMenu).filter(RoleMenu.role_id.in_(role_ids)).delete(
                synchronize_session=False,
            )
        tenant = session.query(Tenant).filter(Tenant.id == 1).first()
        if tenant is not None:
            tenant.package_id = None
        session.commit()
    finally:
        session.close()
        engine.dispose()


def _assert_package_grants(session) -> None:
    """套餐、套餐菜单、R1 角色菜单必须和当前菜单数一致。"""
    from app.domains.sys.models import (
        Menu,
        Role,
        RoleMenu,
        Tenant,
        TenantPackage,
        TenantPackageMenu,
    )
    from tools.seed.access import DEFAULT_PACKAGE_NAME

    menus = session.query(Menu).filter(Menu.deleted == 0).count()
    assert menus > 0
    package = session.query(TenantPackage).filter(
        TenantPackage.name == DEFAULT_PACKAGE_NAME,
        TenantPackage.deleted == 0,
    ).one()
    package_menus = session.query(TenantPackageMenu).filter(
        TenantPackageMenu.package_id == package.id,
    ).count()
    role = session.query(Role).filter(
        Role.tenant_id == 1, Role.role_key == "R1", Role.deleted == 0,
    ).one()
    role_menus = session.query(RoleMenu).filter(RoleMenu.role_id == role.id).count()
    tenant = session.query(Tenant).filter(Tenant.id == 1).one()
    assert package_menus == menus
    assert role_menus == menus
    assert tenant.package_id == package.id


def _prepare_real_db(tmp_path: Path) -> tuple[str, str, object]:
    """建表、清掉旧套餐授权，再执行 e2e 种子。不替换 get_db。"""
    from app.db.base import Base
    from app.db.session import _db_session
    from app.domains.sys import models  # noqa: F401
    from app.main import app

    assert app.dependency_overrides == {}
    context_token = _db_session.set(None)
    db_url, original_url = _shared_url(tmp_path)
    schema_engine = create_engine(db_url)
    Base.metadata.create_all(schema_engine)
    schema_engine.dispose()
    _strip_package_grants(db_url)

    env = os.environ.copy()
    env["IMS_DB_URL"] = db_url
    env.setdefault("IMS_JWT_SECRET", "test-jwt-secret-key-for-testing-only")
    # e2e 启动校验要求 redis.url 非空；种子本身不连 Redis。
    if not env.get("IMS_REDIS_URL"):
        env["IMS_REDIS_URL"] = "redis://127.0.0.1:6379/0"
    seeded = subprocess.run(
        [sys.executable, "-m", "tools.seed", "--env", "e2e"],
        cwd=BACKEND_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert seeded.returncode == 0, seeded.stdout + "\n" + seeded.stderr
    return db_url, original_url, context_token


def _release_real_db(original_url: str, context_token: object) -> None:
    from app.core.config import get_settings
    from app.db.session import _db_session

    get_settings().db.url = original_url
    _db_session.reset(context_token)


def _walk_menus(nodes: list) -> list[dict]:
    found: list[dict] = []
    for node in nodes:
        found.append(node)
        found.extend(_walk_menus(node.get("children") or []))
    return found


def _login(client: TestClient, username: str, password: str) -> str:
    """真实登录，返回访问令牌。不伪造令牌，也不替换依赖。"""
    login = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["code"] == 0, login_body
    token = login_body["data"]["accessToken"]
    assert isinstance(token, str) and token.count(".") == 2
    return token


def _login_me(client: TestClient, username: str, password: str) -> dict:
    """真实登录后请求 /me。"""
    token = _login(client, username, password)
    me = client.get(
        "/admin-api/ims/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["code"] == 0, me_body
    return me_body


def test_real_login_me_and_health(tmp_path):
    """种子用户登录后 /me 返回菜单，/health 的 db 为 UP，登录时间已提交。"""
    from app.domains.sys.models import User
    from app.main import app
    from tools.seed.users import E2E_PASSWORD, E2E_USERNAME

    db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        grant_engine, grant_session = _connect(db_url)
        try:
            _assert_package_grants(grant_session)
            seeded_user = grant_session.query(User).filter(User.username == E2E_USERNAME).one()
            seeded_user.last_login_time = datetime(2000, 1, 1)
            grant_session.commit()
            grant_session.refresh(seeded_user)
            login_before = seeded_user.last_login_time
        finally:
            grant_session.close()
            grant_engine.dispose()
        assert login_before is not None

        with TestClient(app) as client:
            logged_out = client.get("/admin-api/ims/auth/me")
            assert logged_out.status_code == 401
            assert logged_out.json()["code"] == 1002

            health = client.get("/health")
            assert health.status_code == 200
            health_body = health.json()
            assert health_body["code"] == 0
            assert health_body["data"]["db"] == "UP"
            assert db_url not in health.text

            me_body = _login_me(client, E2E_USERNAME, E2E_PASSWORD)
            assert me_body["data"]["user"]["username"] == "test_admin"
            menus = me_body["data"]["menus"]
            assert isinstance(menus, list)
            assert len(menus) > 0
            assert any(item["name"] == "部门管理" for item in _walk_menus(menus))

        check_engine, check = _connect(db_url)
        try:
            _assert_package_grants(check)
            user = check.query(User).filter(User.username == E2E_USERNAME).one()
            # 新连接看不到未提交的 flush。已有登录时间时，必须变成这次登录的新值。
            assert user.last_login_time is not None
            assert user.last_login_time != login_before
        finally:
            check.close()
            check_engine.dispose()
    finally:
        _release_real_db(original_url, context_token)


def test_test_admin_me_includes_system_and_auth_menus(tmp_path):
    """test_admin 真实登录后，/me 同时包含系统管理和权限管理。"""
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    _db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            me_body = _login_me(client, "test_admin", E2E_PASSWORD)
            assert me_body["data"]["user"]["username"] == "test_admin"
            names = {item["name"] for item in me_body["data"]["menus"]}
            assert "系统管理" in names
            assert "权限管理" in names
    finally:
        _release_real_db(original_url, context_token)


def _assert_auth_leaves(menus: list) -> dict:
    """01 清单第 45 行：权限管理下两个叶子的名称、父级、path、权限码。"""
    auth = next(item for item in menus if item["name"] == "权限管理")
    assert auth["type"] == "DIR"
    assert auth["path"] == "/ims/auth"
    children = auth["children"]
    assert [item["name"] for item in children] == ["组织架构同步", "岗位-角色供给规则"]
    org_sync, position = children
    # 第 32 行查看码挂在组织同步叶子上，path 不是 B0a 占位 /system/org-sync。
    assert org_sync["name"] == "组织架构同步"
    assert org_sync["path"] == "/ims/auth/org"
    assert org_sync["permCode"] == "ims:system:org-sync:query"
    assert org_sync["type"] == "MENU"
    assert org_sync["parentId"] == auth["id"]
    assert not org_sync.get("children")
    # 第 35 行查看码挂在岗位规则叶子上。
    assert position["name"] == "岗位-角色供给规则"
    assert position["path"] == "/ims/auth/position"
    assert position["permCode"] == "ims:auth:position-rule:query"
    assert position["type"] == "MENU"
    assert position["parentId"] == auth["id"]
    assert not position.get("children")
    nodes = _walk_menus(menus)
    assert "/system/org-sync" not in {item.get("path") for item in nodes}
    assert "BUTTON" not in {item["type"] for item in nodes}
    return auth


def test_auth_menu_children_are_org_and_position_without_buttons(tmp_path):
    """第 45 行：权限管理下只有组织架构同步和岗位规则，树里没有按钮。"""
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    _db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            me_body = _login_me(client, "test_admin", E2E_PASSWORD)
            menus = me_body["data"]["menus"]
            _assert_auth_leaves(menus)

            nodes = _walk_menus(menus)
            assert "执行同步" not in {item["name"] for item in nodes}
            assert "新建规则" not in {item["name"] for item in nodes}
            perms = set(me_body["data"]["permCodes"])
            # 按钮不进菜单树，R1 仍能在 permCodes 里看到第 33、36 行。
            assert "ims:system:org-sync:run" in perms
            assert "ims:auth:position-rule:create" in perms
    finally:
        _release_real_db(original_url, context_token)


def test_r1_r2_r4_me_auth_leaves_follow_feature_list(tmp_path):
    """第 32、35 行：R1、R2、R4 都能在 /me 菜单树里看到两个叶子；写操作只有 R1。"""
    from app.main import app
    from tools.seed.grants import B1_PERM_ALL, B1_PERM_READONLY
    from tools.seed.users import E2E_PASSWORD

    # 第 32、34、35 行三方都有；第 33、36–39 行只有 R1。
    shared = {
        "ims:system:org-sync:query",
        "ims:system:org-sync:export",
        "ims:auth:position-rule:query",
    }
    r1_only = {
        "ims:system:org-sync:run",
        "ims:auth:position-rule:create",
        "ims:auth:position-rule:update",
        "ims:auth:position-rule:delete",
        "ims:auth:position-rule:refresh",
    }
    assert shared == set(B1_PERM_READONLY)
    assert shared | r1_only == set(B1_PERM_ALL)

    _db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            admin = _login_me(client, "test_admin", E2E_PASSWORD)
            admin_menus = admin["data"]["menus"]
            _assert_auth_leaves(admin_menus)
            admin_names = {item["name"] for item in admin_menus}
            assert "系统管理" in admin_names
            assert "权限管理" in admin_names
            admin_codes = set(admin["data"]["permCodes"])
            assert shared <= admin_codes
            assert r1_only <= admin_codes

            for username in ("test_xz", "test_yyzj"):
                body = _login_me(client, username, E2E_PASSWORD)
                menus = body["data"]["menus"]
                _assert_auth_leaves(menus)
                # R2、R4 本批只挂权限管理，看不到系统管理和写操作按钮码。
                assert [item["name"] for item in menus] == ["权限管理"]
                codes = set(body["data"]["permCodes"])
                assert codes == shared
                assert r1_only.isdisjoint(codes)
    finally:
        _release_real_db(original_url, context_token)


def test_r10_me_only_workbench_and_other_api_forbidden(tmp_path):
    """test_r10 真实登录后 /me 只有工作台，其它受保护接口返回 1008。"""
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    _db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            token = _login(client, "test_r10", E2E_PASSWORD)
            me = client.get(
                "/admin-api/ims/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me.status_code == 200
            me_body = me.json()
            assert me_body["code"] == 0, me_body
            nodes = _walk_menus(me_body["data"]["menus"])
            assert [item["name"] for item in nodes] == ["工作台"]
            assert nodes[0]["type"] == "MENU"
            assert nodes[0]["path"] == "/ims/workbench"
            assert "BUTTON" not in {item["type"] for item in nodes}
            assert "ims:system:user:query" not in set(me_body["data"]["permCodes"])

            forbidden = client.get(
                "/admin-api/ims/system/user/page",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert forbidden.status_code == 200
            assert forbidden.json()["code"] == 1008
    finally:
        _release_real_db(original_url, context_token)
