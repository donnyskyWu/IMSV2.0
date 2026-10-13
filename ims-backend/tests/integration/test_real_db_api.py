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
            # 部门管理挂在「系统管理」目录下，不在根上。
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


def test_me_menu_parent_points_at_directory(tmp_path):
    """种子 parent_id 为目录→菜单→按钮。/me 中菜单 parentId 指向目录，按钮只在 permCodes。"""
    from app.domains.sys.models import Menu
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        engine, session = _connect(db_url)
        try:
            rows = session.query(Menu).filter(Menu.deleted == 0).all()
            by_id = {row.id: row for row in rows}
            auth = next(row for row in rows if row.type == "DIR" and row.name == "权限管理")
            auth_menus = [row for row in rows if row.parent_id == auth.id]
            assert [row.name for row in sorted(auth_menus, key=lambda item: item.sort)] == [
                "组织架构同步",
                "岗位-角色供给规则",
            ]
            assert {row.type for row in auth_menus} == {"MENU"}
            for row in rows:
                if row.type == "DIR":
                    assert (row.parent_id or 0) == 0, row.name
                elif row.type == "MENU" and row.path == "/ims/workbench":
                    # 工作台是顶层菜单，不挂目录。
                    assert (row.parent_id or 0) == 0
                elif row.type == "MENU":
                    parent = by_id[row.parent_id]
                    assert parent.type == "DIR", row.name
                elif row.type == "BUTTON":
                    parent = by_id[row.parent_id]
                    assert parent.type == "MENU", row.name
            button_codes = {
                row.perm_code for row in rows if row.type == "BUTTON" and row.perm_code
            }
            button_names = {row.name for row in rows if row.type == "BUTTON"}
        finally:
            session.close()
            engine.dispose()

        with TestClient(app) as client:
            me_body = _login_me(client, "test_admin", E2E_PASSWORD)
            menus = me_body["data"]["menus"]
            root_names = [item["name"] for item in menus]
            assert "组织架构同步" not in root_names
            assert "岗位-角色供给规则" not in root_names
            assert all(item.get("parentId") is None for item in menus)

            auth_node = next(item for item in menus if item["name"] == "权限管理")
            assert auth_node["type"] == "DIR"
            assert [item["name"] for item in auth_node["children"]] == [
                "组织架构同步",
                "岗位-角色供给规则",
            ]
            for directory in menus:
                if directory["type"] != "DIR":
                    continue
                assert directory["children"], directory["name"]
                for child in directory["children"]:
                    assert child["type"] == "MENU"
                    assert child["parentId"] == directory["id"]
                    assert not child.get("children")

            nodes = _walk_menus(menus)
            assert "BUTTON" not in {item["type"] for item in nodes}
            assert button_names.isdisjoint({item["name"] for item in nodes})
            assert button_codes <= set(me_body["data"]["permCodes"])
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
            assert [item["name"] for item in nodes] == ["个人工作台"]
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
            # B1 组织同步查询（ims:system:org-sync:query）。R10 没有这个码，同样 1008。
            org_sync = client.get(
                "/admin-api/ims/system/org-sync/latest-batch",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert org_sync.status_code == 200
            assert org_sync.json()["code"] == 1008
    finally:
        _release_real_db(original_url, context_token)


def test_real_lock_freeze_and_password_change(tmp_path):
    """真实库覆盖锁定、冻结/离职和改密。不替换 get_db，也不替换鉴权。"""
    from app.domains.sys.models import LoginLog, User
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            for _ in range(4):
                wrong = client.post(
                    "/admin-api/ims/auth/login",
                    json={"username": "test_lock", "password": "Wrong1234"},
                )
                assert wrong.status_code == 200
                assert wrong.json()["code"] == 1214

            locked = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_lock", "password": "Wrong1234"},
            )
            locked_body = locked.json()
            assert locked_body["code"] == 1215, locked_body
            assert locked_body["data"]["remainMinutes"] == 15
            assert "15" in locked_body["msg"]

            still = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_lock", "password": E2E_PASSWORD},
            )
            still_body = still.json()
            assert still_body["code"] == 1215
            assert still_body["data"]["remainMinutes"] == 15

            frozen_wrong = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_frozen", "password": "Wrong1234"},
            )
            assert frozen_wrong.json()["code"] == 1214
            frozen = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_frozen", "password": E2E_PASSWORD},
            )
            assert frozen.json()["code"] == 1216
            resigned = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_resigned", "password": E2E_PASSWORD},
            )
            assert resigned.json()["code"] == 1216

            tenant = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_t2", "password": E2E_PASSWORD},
            )
            tenant_body = tenant.json()
            assert tenant_body["code"] == 1008
            assert tenant_body["msg"] == "所属组织已停用，请联系管理员"

            first = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_reset", "password": E2E_PASSWORD},
            )
            first_body = first.json()
            assert first_body["code"] == 0, first_body
            assert first_body["data"]["pwdResetRequired"] is True
            token = first_body["data"]["accessToken"]
            headers = {"Authorization": f"Bearer {token}"}

            other = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_reset", "password": E2E_PASSWORD},
            )
            other_token = other.json()["data"]["accessToken"]

            me_before = client.get("/admin-api/ims/auth/me", headers=headers)
            assert me_before.status_code == 200
            assert me_before.json()["data"]["user"]["pwdResetRequired"] is True

            blocked = client.get("/admin-api/ims/system/dict-type/list", headers=headers)
            assert blocked.json()["code"] == 1008

            bad_old = client.post(
                "/admin-api/ims/auth/password/change",
                headers=headers,
                json={"oldPassword": "Wrong1234", "newPassword": "Abcd5678!"},
            )
            assert bad_old.json()["code"] == 1214
            weak = client.post(
                "/admin-api/ims/auth/password/change",
                headers=headers,
                json={"oldPassword": E2E_PASSWORD, "newPassword": "abcdefgh"},
            )
            assert weak.json()["code"] == 1001
            changed = client.post(
                "/admin-api/ims/auth/password/change",
                headers=headers,
                json={"oldPassword": E2E_PASSWORD, "newPassword": "Abcd5678!"},
            )
            assert changed.json()["code"] == 0, changed.json()

            kept = client.get("/admin-api/ims/auth/me", headers=headers)
            assert kept.status_code == 200
            assert kept.json()["data"]["user"]["pwdResetRequired"] is False
            dropped = client.get(
                "/admin-api/ims/auth/me",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            assert dropped.status_code == 401
            assert dropped.json()["code"] == 1002

            old_login = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_reset", "password": E2E_PASSWORD},
            )
            assert old_login.json()["code"] == 1214
            new_login = client.post(
                "/admin-api/ims/auth/login",
                json={"username": "test_reset", "password": "Abcd5678!"},
            )
            new_body = new_login.json()
            assert new_body["code"] == 0, new_body
            assert new_body["data"]["pwdResetRequired"] is False

        # 失败响应返回之后，新连接仍能看见次数和日志，说明失败先提交了。
        check_engine, check = _connect(db_url)
        try:
            locked_user = check.query(User).filter(User.username == "test_lock").one()
            assert locked_user.login_fail_count == 5
            results = {
                row.result
                for row in check.query(LoginLog).filter(LoginLog.username == "test_lock").all()
            }
            assert "BAD_CREDENTIAL" in results
            assert "LOCKED" in results
            frozen_results = {
                row.result
                for row in check.query(LoginLog).filter(LoginLog.username == "test_frozen").all()
            }
            assert "DISABLED" in frozen_results
        finally:
            check.close()
            check_engine.dispose()
    finally:
        _release_real_db(original_url, context_token)
