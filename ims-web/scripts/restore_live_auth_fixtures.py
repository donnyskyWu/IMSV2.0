#!/usr/bin/env python3
"""恢复 live-proxy 登录夹具。版本：2026-10-13。

LG-05 把 test_lock 写进 Redis 键 ims:login_fail: 和用户行的失败次数。
LG-06 的错密会给 test_frozen 累加次数。
LG-10 会改掉 test_reset 的密码，并清掉须改密标记。

本脚本只改这三行，把计数、锁定截止时间和 test_reset 的口令、须改密标记
恢复成种子状态。口令取 tools.seed.users.E2E_PASSWORD，不另写一套。
锁定计数在 Redis，必须和 API 使用同一个 IMS_REDIS_URL，内存缓存清不掉。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "ims-backend"
sys.path.insert(0, str(BACKEND))

# 这三行对应 02 §0.2。只清它们，避免误改 test_admin 等其他用例账号。
LOCK_USERNAMES = ("test_lock", "test_frozen")
RESET_USERNAME = "test_reset"
LOGIN_FAIL_PREFIX = "ims:login_fail:"


def main() -> None:
    db_url = os.environ.get("IMS_DB_URL")
    redis_url = os.environ.get("IMS_REDIS_URL")
    if not db_url:
        raise SystemExit("缺少 IMS_DB_URL")
    if not redis_url:
        raise SystemExit("缺少 IMS_REDIS_URL，锁定次数在 Redis 里，不能靠内存缓存恢复")

    from sqlalchemy.engine.url import make_url
    from tools.seed.users import E2E_PASSWORD

    import bcrypt
    import pymysql
    import redis

    url = make_url(db_url)
    if not (url.drivername or "").startswith("mysql"):
        raise SystemExit(f"只支持 MySQL，当前是 {url.drivername}")

    # 与种子相同的 cost，恢复口令的耗时和登录校验同一量级。
    password_hash = bcrypt.hashpw(E2E_PASSWORD.encode(), bcrypt.gensalt(rounds=10)).decode()
    connection = pymysql.connect(
        host=url.host or "127.0.0.1",
        port=url.port or 3306,
        user=url.username or "",
        password=url.password or "",
        database=url.database or "",
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with connection.cursor() as cursor:
            # 用户名唯一键 (tenant_id, username, deleted)，这三条查询只命中各一行。
            names = (*LOCK_USERNAMES, RESET_USERNAME)
            cursor.execute(
                """
                SELECT username
                FROM ims_sys_user
                WHERE deleted = 0 AND username IN (%s, %s, %s)
                """,
                names,
            )
            found = {row[0] for row in cursor.fetchall()}
            missing = [name for name in names if name not in found]
            if missing:
                raise SystemExit(f"种子账号不存在: {', '.join(missing)}")

            cursor.execute(
                """
                UPDATE ims_sys_user
                SET login_fail_count = 0,
                    lock_until = NULL
                WHERE deleted = 0 AND username IN (%s, %s)
                """,
                LOCK_USERNAMES,
            )
            cursor.execute(
                """
                UPDATE ims_sys_user
                SET password_hash = %s,
                    pwd_reset_required = 1,
                    login_fail_count = 0,
                    lock_until = NULL
                WHERE deleted = 0 AND username = %s
                """,
                (password_hash, RESET_USERNAME),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    client = redis.from_url(redis_url, decode_responses=True)
    client.ping()
    # 登录失败次数以这个键为准。只删三个账号，不 FLUSHDB。
    client.delete(*(f"{LOGIN_FAIL_PREFIX}{name}" for name in (*LOCK_USERNAMES, RESET_USERNAME)))
    print("restored test_lock, test_frozen, test_reset")


if __name__ == "__main__":
    main()
