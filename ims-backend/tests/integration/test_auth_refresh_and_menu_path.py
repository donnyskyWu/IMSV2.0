# tests/integration/test_auth_refresh_and_menu_path.py
"""刷新令牌轮换和 /me 叶子 path。

不替换 get_db，也不 mock AuthService。
并发与原子性断言只打真实 Redis，不用 fakeredis。
叶子 path 取主干 tools/seed/menus.py，不另造工作台或 B1 路由。
"""
import asyncio
import threading
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.errors import BizError


def _run(coro):
    """跑完协程后给主线程补一个事件循环。

    asyncio.run 会关掉当前循环。仓库里旧用例还在调用 get_event_loop()，
    循环被关掉之后它们会直接报错。新用例本身不调用 get_event_loop。
    """
    try:
        return asyncio.run(coro)
    finally:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _require_real_redis():
    """并发测试必须连上 redis 包的客户端。内存回退直接失败。"""
    import app.core.cache as cache_mod
    from app.core.cache import init_cache

    init_cache()
    client = cache_mod._redis_client
    module = type(client).__module__ if client is not None else ""
    if client is None or not module.startswith("redis") or "fakeredis" in module:
        pytest.fail(
            "刷新令牌并发测试必须连接真实 Redis（IMS_REDIS_URL），不能回退内存或 fakeredis"
        )
    assert client.ping() is True
    return client


@pytest.fixture
def real_redis():
    return _require_real_redis()


@pytest.fixture
def app_client(db_session, test_context):
    from app.main import app

    with TestClient(app) as client:
        yield client


def _password_hash() -> str:
    import bcrypt

    return bcrypt.hashpw(b"Test1234", bcrypt.gensalt(rounds=4)).decode()


def _add_user(db_session, username: str):
    from tests.support.rows import user

    return user(db_session, username, password_hash=_password_hash())


def _login(client: TestClient, username: str) -> dict:
    response = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Test1234"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0, body
    return body["data"]


def _refresh(client: TestClient, refresh_token: str):
    return client.post(
        "/admin-api/ims/auth/refresh-token",
        json={"refreshToken": refresh_token},
    )


def _auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _sid(access_token: str) -> str:
    from app.core.config import get_settings

    settings = get_settings()
    payload = jwt.decode(
        access_token,
        settings.jwt.secret,
        algorithms=[settings.jwt.algorithm],
    )
    return payload["sid"]


def test_refresh_rotates_and_reused_token_revokes_session(
    app_client, db_session, real_redis, test_context,
):
    """轮换签发新令牌；重放旧刷新令牌失败，并把刚签发的 access/refresh 一并作废。"""
    user = _add_user(db_session, "rotate_user")
    other = _login(app_client, _add_user(db_session, "other_device").username)
    first = _login(app_client, user.username)
    # 同一用户再开一个会话，重放只应吊销被轮换的那一段。
    second = _login(app_client, user.username)

    refreshed = _refresh(app_client, first["refreshToken"])
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    assert refreshed_body["code"] == 0, refreshed_body
    new_access = refreshed_body["data"]["accessToken"]
    new_refresh = refreshed_body["data"]["refreshToken"]
    assert new_access
    assert new_refresh != first["refreshToken"]

    me = app_client.get("/admin-api/ims/auth/me", headers=_auth(new_access))
    assert me.status_code == 200
    assert me.json()["code"] == 0

    reused = _refresh(app_client, first["refreshToken"])
    assert reused.status_code == 401
    assert reused.json()["code"] == 1002

    me_after = app_client.get("/admin-api/ims/auth/me", headers=_auth(new_access))
    assert me_after.status_code == 401
    assert me_after.json()["code"] == 1002
    new_refresh_after = _refresh(app_client, new_refresh)
    assert new_refresh_after.status_code == 401
    assert new_refresh_after.json()["code"] == 1002

    # 另一个会话的刷新令牌还在。
    kept = _refresh(app_client, second["refreshToken"])
    assert kept.status_code == 200
    assert kept.json()["code"] == 0
    assert _refresh(app_client, other["refreshToken"]).status_code == 200


def test_unknown_refresh_getdel_empty_does_not_revoke_live_session(
    app_client, db_session, real_redis, test_context,
):
    """GETDEL 为空且没有已轮换记录时只返回 1002，不误伤还活着的会话。"""
    user = _add_user(db_session, "empty_getdel")
    live = _login(app_client, user.username)

    unknown = _refresh(app_client, "missing-token")
    assert unknown.status_code == 401
    assert unknown.json()["code"] == 1002

    empty = _refresh(app_client, "")
    assert empty.status_code == 401
    assert empty.json()["code"] == 1002

    still = _refresh(app_client, live["refreshToken"])
    assert still.status_code == 200
    assert still.json()["code"] == 0


def test_concurrent_refresh_exactly_one_succeeds(
    app_client, db_session, real_redis, test_context,
):
    """同一枚刷新令牌并发提交，恰好一个成功，成功换到的令牌仍然有效。"""
    from sqlalchemy.orm import sessionmaker

    from app.db.session import _db_session
    from app.services.auth import AuthService

    user = _add_user(db_session, "race_user")
    db_session.flush()
    first = _login(app_client, user.username)
    db_session.commit()
    refresh_token = first["refreshToken"]
    engine = db_session.get_bind()
    # 两个线程都走到 Lua 再一起执行，避免后到的请求被当成重放。
    at_claim = threading.Barrier(2)
    real_eval = real_redis.eval

    def synced_eval(*args, **kwargs):
        script = args[0] if args else ""
        if isinstance(script, str) and "GETDEL" in script:
            at_claim.wait(timeout=5)
        return real_eval(*args, **kwargs)

    real_redis.eval = synced_eval
    results: list = []
    results_lock = threading.Lock()

    def worker() -> None:
        session = sessionmaker(bind=engine)()
        handle = _db_session.set(session)
        try:
            try:
                value = asyncio.run(AuthService().refresh(refresh_token))
            except BizError as exc:
                value = exc
        finally:
            _db_session.reset(handle)
            session.close()
        with results_lock:
            results.append(value)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    real_redis.eval = real_eval

    assert len(results) == 2
    oks = [item for item in results if isinstance(item, dict)]
    errors = [item for item in results if isinstance(item, BizError)]
    assert len(oks) == 1
    assert len(errors) == 1
    assert errors[0].code == 1002

    verified = _run(AuthService().verify_token(oks[0]["access_token"]))
    assert verified["user_id"] == user.id
    again = _run(AuthService().refresh(oks[0]["refresh_token"]))
    assert again["refresh_token"] != oks[0]["refresh_token"]


def test_logout_and_change_password_reject_old_refresh(
    app_client, db_session, real_redis, test_context,
):
    """登出后该会话的刷新令牌失效；改密后其它会话的刷新令牌失效，当前会话仍可刷新。"""
    from app.services.auth import AuthService

    user = _add_user(db_session, "logout_user")
    logged_in = _login(app_client, user.username)
    logout = app_client.post(
        "/admin-api/ims/auth/logout",
        headers=_auth(logged_in["accessToken"]),
    )
    assert logout.status_code == 200
    assert logout.json()["code"] == 0
    after_logout = _refresh(app_client, logged_in["refreshToken"])
    assert after_logout.status_code == 401
    assert after_logout.json()["code"] == 1002
    me = app_client.get(
        "/admin-api/ims/auth/me",
        headers=_auth(logged_in["accessToken"]),
    )
    assert me.status_code == 401

    changer = _add_user(db_session, "change_pw")
    current = _login(app_client, changer.username)
    other = _login(app_client, changer.username)
    _run(AuthService().change_password(
        changer.id,
        "Newpass123",
        _sid(current["accessToken"]),
    ))
    dropped = _refresh(app_client, other["refreshToken"])
    assert dropped.status_code == 401
    assert dropped.json()["code"] == 1002
    kept = _refresh(app_client, current["refreshToken"])
    assert kept.status_code == 200
    assert kept.json()["code"] == 0


def test_refresh_rejects_blocked_missing_and_frozen_sessions(
    app_client, db_session, real_redis, test_context,
):
    """会话对不上、被拉黑、用户不存在或已冻结时，刷新返回 1002。"""
    from app.core.cache import Cache
    from app.domains.sys.models import User
    from app.services.auth import AuthService

    service = AuthService()

    def _open(username: str) -> tuple[dict, str]:
        person = _add_user(db_session, username)
        tokens = _login(app_client, person.username)
        session_id = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{tokens['refreshToken']}")
        assert session_id
        return tokens, session_id

    mismatch, mismatch_sid = _open("refresh_mismatch")
    session_key = f"{service.SESSION_PREFIX}{mismatch_sid}"
    stored = Cache.get_json(session_key)
    stored["refresh_token"] = "other-token"
    Cache.set_json(session_key, stored)
    mismatch_resp = _refresh(app_client, mismatch["refreshToken"])
    assert mismatch_resp.status_code == 401
    assert mismatch_resp.json()["code"] == 1002

    blocked, blocked_sid = _open("refresh_blocked")
    Cache.set(f"{service.TOKEN_BLACKLIST_PREFIX}{blocked_sid}", "1", ttl=60)
    blocked_resp = _refresh(app_client, blocked["refreshToken"])
    assert blocked_resp.status_code == 401
    assert blocked_resp.json()["code"] == 1002

    missing_user, missing_sid = _open("refresh_missing_user")
    missing_key = f"{service.SESSION_PREFIX}{missing_sid}"
    payload = Cache.get_json(missing_key)
    payload["user_id"] = 999999
    Cache.set_json(missing_key, payload)
    missing_resp = _refresh(app_client, missing_user["refreshToken"])
    assert missing_resp.status_code == 401
    assert missing_resp.json()["code"] == 1002

    gone, gone_sid = _open("refresh_gone")
    Cache.delete(f"{service.SESSION_PREFIX}{gone_sid}")
    gone_resp = _refresh(app_client, gone["refreshToken"])
    assert gone_resp.status_code == 401
    assert gone_resp.json()["code"] == 1002

    frozen_user = _add_user(db_session, "refresh_frozen")
    frozen_tokens = _login(app_client, frozen_user.username)
    row = db_session.query(User).filter(User.username == "refresh_frozen").one()
    row.status = "FROZEN"
    db_session.flush()
    frozen_resp = _refresh(app_client, frozen_tokens["refreshToken"])
    assert frozen_resp.status_code == 401
    assert frozen_resp.json()["code"] == 1002

    resigned_user = _add_user(db_session, "refresh_resigned")
    resigned_tokens = _login(app_client, resigned_user.username)
    resigned = db_session.query(User).filter(User.username == "refresh_resigned").one()
    resigned.status = "RESIGNED"
    db_session.flush()
    resigned_resp = _refresh(app_client, resigned_tokens["refreshToken"])
    assert resigned_resp.status_code == 401
    assert resigned_resp.json()["code"] == 1002


def test_logout_without_refresh_index_and_revoke_missing_session(
    db_session, real_redis, test_context,
):
    """没有刷新索引的会话也能登出；重放时会话键已经没了，仍然记黑名单。"""
    from app.core.cache import Cache
    from app.core.clock import get_now
    from app.core.config import get_settings
    from app.services.auth import AuthService

    settings = get_settings()
    service = AuthService()
    now = get_now()
    session_id = "logout-no-refresh"
    Cache.set_json(
        f"{service.SESSION_PREFIX}{session_id}",
        {"user_id": 1},
        ttl=60,
    )
    token = jwt.encode(
        {
            "sub": "1",
            "tid": "1",
            "sid": session_id,
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "type": "access",
        },
        settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
    )
    _run(service.logout(token))
    assert Cache.get_json(f"{service.SESSION_PREFIX}{session_id}") is None

    user = _add_user(db_session, "revoke_gap")
    # 直接标成已轮换，但会话键先删掉，覆盖吊销时读不到会话的分支。
    used_token = "already-rotated"
    Cache.set(f"{service.REFRESH_USED_PREFIX}{used_token}", "missing-sid", ttl=60)
    with pytest.raises(BizError) as exc_info:
        _run(service.refresh(used_token))
    assert exc_info.value.code == 1002
    assert Cache.get(f"{service.TOKEN_BLACKLIST_PREFIX}missing-sid") == "1"
    assert user.id


def test_me_menu_nodes_return_seed_leaf_paths(app_client, db_session, test_context):
    """/me 的 MENU 节点带回主干种子里的 path，字段仍是 path，不新造工作台路由。"""
    from app.domains.sys.models import Menu
    from tests.support.rows import add, bind_menu, bind_role, role
    from tools.seed.menus import MENUS

    def insert(nodes: list, parent_id: int) -> list:
        created: list = []
        for node in nodes:
            menu = add(db_session, Menu(
                tenant_id=1,
                parent_id=parent_id,
                type=node["type"],
                name=node["name"],
                perm_code=node.get("perm_code"),
                path=node.get("path"),
                status="ENABLED",
                sort=node.get("sort", 0),
                visible=True,
            ))
            created.append(menu)
            created.extend(insert(node.get("children") or [], menu.id))
        return created

    created = insert(MENUS, 0)
    expected = {
        menu.perm_code: menu.path
        for menu in created
        if menu.type == "MENU"
    }
    assert expected
    assert all(path and path.strip() for path in expected.values())
    assert "/ims/workbench" not in expected.values()
    assert "/ims/auth/org" not in expected.values()
    assert "/ims/auth/position" not in expected.values()

    person = _add_user(db_session, "menu_path_user")
    granted = role(db_session, "menu_path_role", "菜单路径")
    for menu in created:
        bind_menu(db_session, granted.id, menu.id)
    bind_role(db_session, person.id, granted.id)

    tokens = _login(app_client, person.username)
    response = app_client.get(
        "/admin-api/ims/auth/me",
        headers=_auth(tokens["accessToken"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0, body
    nodes = body["data"]["menus"]
    leaves = [item for item in nodes if item.get("type") == "MENU"]
    got = {item["permCode"]: item["path"] for item in leaves}
    assert got == expected
    sample = leaves[0]
    assert sample["id"]
    assert sample["name"]
    assert sample["type"] == "MENU"
    assert "permCode" in sample
    directories = [item for item in nodes if item.get("type") == "DIR"]
    assert directories
    assert all(not item.get("path") for item in directories)
