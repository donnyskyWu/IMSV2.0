"""真实数据库上的 HTTP 集成测试。

不使用 dependency_overrides，也不替换 get_db 或会话。
账号由 `python -m tools.seed --env e2e` 写入，密码 Test1234。
CI 使用 workflow 里的 MySQL；本机没配库时退回 IMS_DB_URL。
"""

import os
import subprocess
import sys
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


def _prepare_real_db(tmp_path: Path) -> tuple[str, str, object]:
    """建表并执行 e2e 种子。不替换 get_db，也不预置请求会话。"""
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


def _login_me(client: TestClient, username: str, password: str) -> dict:
    """真实登录后请求 /me。不伪造令牌，也不替换依赖。"""
    login = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["code"] == 0, login_body
    token = login_body["data"]["accessToken"]
    assert isinstance(token, str) and token.count(".") == 2
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
        with TestClient(app) as client:
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

        check_engine = create_engine(db_url)
        check = sessionmaker(bind=check_engine)()
        try:
            user = check.query(User).filter(User.username == E2E_USERNAME).one()
            # 请求结束时提交；只 flush 不 commit 的话这里读不到。
            assert user.last_login_time is not None
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


def test_auth_menu_children_are_org_and_position_without_buttons(tmp_path):
    """权限管理下有组织同步、岗位规则两个子菜单，整棵树没有按钮。

    01/02 的菜单名是「组织架构同步」和「岗位-角色供给规则」。
    按钮只出现在 permCodes。
    """
    from app.main import app
    from tools.seed.users import E2E_PASSWORD

    _db_url, original_url, context_token = _prepare_real_db(tmp_path)
    try:
        with TestClient(app) as client:
            me_body = _login_me(client, "test_admin", E2E_PASSWORD)
            menus = me_body["data"]["menus"]
            auth = next(item for item in menus if item["name"] == "权限管理")
            assert auth["type"] == "DIR"
            children = auth["children"]
            assert [item["name"] for item in children] == ["组织架构同步", "岗位-角色供给规则"]
            assert [item["type"] for item in children] == ["MENU", "MENU"]
            assert [item["parentId"] for item in children] == [auth["id"], auth["id"]]
            assert children[0]["path"] == "/ims/auth/org"
            assert children[1]["path"] == "/ims/auth/position"

            nodes = _walk_menus(menus)
            assert "BUTTON" not in {item["type"] for item in nodes}
            assert "执行同步" not in {item["name"] for item in nodes}
            assert "新建规则" not in {item["name"] for item in nodes}
            perms = set(me_body["data"]["permCodes"])
            assert "ims:system:org-sync:run" in perms
            assert "ims:auth:position-rule:create" in perms
    finally:
        _release_real_db(original_url, context_token)
