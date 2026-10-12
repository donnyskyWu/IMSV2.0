# tests/integration/test_auth_refresh_and_menu_path.py
"""刷新令牌轮换和 /me 叶子 path。

不替换 get_db，也不 mock AuthService。
并发与原子性断言只打真实 Redis，不用 fakeredis。
侧栏两条叶子由本用例按 01 功能点清单的权限码写入，不把主干种子的 path 当成裁定 23 的结果。
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
    # 两个 Lua 都返回之前，先到的线程不能继续跑完轮换并把锁删掉。
    after_claim = threading.Barrier(2)
    real_eval = real_redis.eval

    def synced_eval(*args, **kwargs):
        script = args[0] if args else ""
        if isinstance(script, str) and "GETDEL" in script:
            at_claim.wait(timeout=5)
            try:
                return real_eval(*args, **kwargs)
            finally:
                after_claim.wait(timeout=5)
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
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
    finally:
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


def test_refresh_absolute_seven_day_boundary_and_remaining_ttl(
    app_client, db_session, real_redis, test_context,
):
    """裁定 24：登录起满 7 天绝对失效。差 1 秒能刷新，过 1 秒失败。

    用注入时钟，不 sleep。轮换后在真实 Redis 上读新 refresh 的 TTL，
    等于剩余秒数（整数秒，允许读到 0 或 1），不能被重置成 7 天。
    满 7 天后的 /me 用临近到期时换发的新 access，这枚 access 的 JWT 尚未过期。
    """
    from app.core.cache import Cache
    from app.core.clock import get_now, set_clock
    from app.core.config import get_settings
    from app.services.auth import AuthService

    settings = get_settings()
    full_ttl = settings.jwt.refresh_token_ttl
    service = AuthService()
    start = get_now()

    def freeze(moment) -> None:
        set_clock(lambda: moment)

    near = _add_user(db_session, "abs_near")
    late = _add_user(db_session, "abs_late")
    legacy = _add_user(db_session, "abs_legacy")
    blank = _add_user(db_session, "abs_blank")

    freeze(start)
    near_tokens = _login(app_client, near.username)
    late_tokens = _login(app_client, late.username)
    legacy_tokens = _login(app_client, legacy.username)
    blank_tokens = _login(app_client, blank.username)

    # 提前 3 分钟换发 late 的 access。满 7 天时这枚 JWT 还有将近 2 小时，
    # 之后 /me 的 1002 只能来自会话剩余时间，不是登录时那枚 2 小时 access 自己过期。
    freeze(start + timedelta(seconds=full_ttl - 180))
    rotated_late = _refresh(app_client, late_tokens["refreshToken"])
    assert rotated_late.status_code == 200
    rotated_late_body = rotated_late.json()
    assert rotated_late_body["code"] == 0, rotated_late_body
    fresh_access = rotated_late_body["data"]["accessToken"]
    fresh_refresh = rotated_late_body["data"]["refreshToken"]
    assert fresh_access
    assert fresh_refresh != late_tokens["refreshToken"]

    # 7 天差 1 秒：还能刷新。Redis TTL 是整数秒，立刻读可能是 0 或 1，但不能回到 7 天。
    freeze(start + timedelta(seconds=full_ttl - 1))
    refreshed = _refresh(app_client, near_tokens["refreshToken"])
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    assert refreshed_body["code"] == 0, refreshed_body
    new_access = refreshed_body["data"]["accessToken"]
    new_refresh = refreshed_body["data"]["refreshToken"]
    assert new_access
    assert new_refresh != near_tokens["refreshToken"]
    # 新 access 的 iat 跟着注入时钟走，会落到真实时间的未来。PyJWT 默认用墙钟，
    # 所以会话 id 从 Redis 的刷新索引读，不解码 JWT。TTL 要立刻读。
    session_id = real_redis.get(f"{service.REFRESH_INDEX_PREFIX}{new_refresh}")
    assert session_id
    refresh_ttl = real_redis.ttl(f"{service.REFRESH_INDEX_PREFIX}{new_refresh}")
    session_ttl = real_redis.ttl(f"{service.SESSION_PREFIX}{session_id}")
    assert refresh_ttl in (0, 1)
    assert session_ttl in (0, 1)
    assert refresh_ttl != full_ttl
    assert session_ttl != full_ttl
    stored = Cache.get_json(f"{service.SESSION_PREFIX}{session_id}")
    assert stored["expires_at"] == (start + timedelta(seconds=full_ttl)).isoformat()

    # 旧数据没有 expires_at 时，用登录时间 + 7 天，同样不续期。
    legacy_sid = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{legacy_tokens['refreshToken']}")
    legacy_key = f"{service.SESSION_PREFIX}{legacy_sid}"
    legacy_data = Cache.get_json(legacy_key)
    legacy_data.pop("expires_at", None)
    legacy_data["created_at"] = start.isoformat()
    Cache.set_json(legacy_key, legacy_data, ttl=full_ttl)
    legacy_refreshed = _refresh(app_client, legacy_tokens["refreshToken"])
    assert legacy_refreshed.status_code == 200
    legacy_body = legacy_refreshed.json()
    assert legacy_body["code"] == 0, legacy_body
    legacy_new = legacy_body["data"]["refreshToken"]
    legacy_ttl = real_redis.ttl(f"{service.REFRESH_INDEX_PREFIX}{legacy_new}")
    assert legacy_ttl in (0, 1)
    assert legacy_ttl != full_ttl

    # 没有登录时间也没有到期时间：按已过期拒绝。
    blank_sid = Cache.get(f"{service.REFRESH_INDEX_PREFIX}{blank_tokens['refreshToken']}")
    blank_key = f"{service.SESSION_PREFIX}{blank_sid}"
    blank_data = Cache.get_json(blank_key)
    blank_data.pop("expires_at", None)
    blank_data.pop("created_at", None)
    Cache.set_json(blank_key, blank_data, ttl=full_ttl)
    blank_resp = _refresh(app_client, blank_tokens["refreshToken"])
    assert blank_resp.status_code == 401
    assert blank_resp.json()["code"] == 1002

    # 过 1 秒：临近到期换发的 refresh 不能再换，那枚新 access 调 /me 也是 1002。
    # 先打 /me。若先重放旧 refresh，会走吊销分支，1002 就不是剩余时间到点。
    freeze(start + timedelta(seconds=full_ttl + 1))
    fresh_claims = jwt.decode(
        fresh_access,
        settings.jwt.secret,
        algorithms=[settings.jwt.algorithm],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert fresh_claims["exp"] > get_now().timestamp()
    late_me = app_client.get(
        "/admin-api/ims/auth/me",
        headers=_auth(fresh_access),
    )
    assert late_me.status_code == 401
    assert late_me.json()["code"] == 1002
    late_resp = _refresh(app_client, fresh_refresh)
    assert late_resp.status_code == 401
    assert late_resp.json()["code"] == 1002


def test_me_menu_paths_use_feature_list_codes_inserted_by_test(
    app_client, db_session, test_context,
):
    """/me 的 MENU 节点带回 path。裁定 23：不新造工作台路由。

    下面两条侧栏不是主干种子里的 path，是本用例自己写入的占位。
    B1 种子落地前，权限码用 01 功能点清单里的码，path 仍是清单路由：
    - ims:system:org-sync:query → /ims/auth/org
    - ims:auth:position-rule:query → /ims/auth/position
    组织同步在种子模板里已有同名权限码（path 为 /system/org-sync）。
    本用例插入时把 path 改成清单占位，避免 perm_code 唯一约束冲突。
    岗位规则种子里没有，由本用例额外插入。
    """
    from app.domains.sys.models import Menu
    from tests.support.rows import add, bind_menu, bind_role, role
    from tools.seed.menus import MENUS

    # 插入种子模板时改掉组织同步的 path。权限码保持清单里的 ims:system:org-sync:query。
    placeholder_path = {
        "ims:system:org-sync:query": "/ims/auth/org",
    }

    def insert(nodes: list, parent_id: int) -> list:
        created: list = []
        for node in nodes:
            perm_code = node.get("perm_code")
            menu = add(db_session, Menu(
                tenant_id=1,
                parent_id=parent_id,
                type=node["type"],
                name=node["name"],
                perm_code=perm_code,
                path=placeholder_path.get(perm_code, node.get("path")),
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
    # 岗位规则不在主干种子里，本用例自己插入。权限码用清单里的 ims:auth:position-rule:query。
    position_rule = add(db_session, Menu(
        tenant_id=1,
        parent_id=0,
        type="MENU",
        name="岗位-角色供给规则",
        perm_code="ims:auth:position-rule:query",
        path="/ims/auth/position",
        status="ENABLED",
        sort=0,
        visible=True,
    ))
    created.append(position_rule)
    expected[position_rule.perm_code] = position_rule.path

    assert expected
    assert all(path and path.strip() for path in expected.values())
    assert "/ims/workbench" not in expected.values()
    assert expected["ims:system:org-sync:query"] == "/ims/auth/org"
    assert expected["ims:auth:position-rule:query"] == "/ims/auth/position"

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
