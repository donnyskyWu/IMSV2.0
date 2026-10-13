# 证件到期扫描（B5 FP-B5-EX）。版本 v1.0 · 2026-10-13
"""每日 08:00 扫描。同一级别只通知一次，升级再通知。"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from app.core.clock import get_now, parse_datetime
from app.core.config import get_settings
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.corp.models import CertExpireTask
from app.domains.shared.models import MasterCert, MasterRealname
from app.domains.sys.models import Menu, Role, RoleMenu, User, UserRole
from app.jobs import job
from app.services.cert import CertService, cert_is_locked, cert_visible_for
from app.services.corp_support import (
    add_row,
    as_text_id,
    base_stmt,
    ensure_write_scope,
    fetch_page,
    get_alive,
    tenant_id,
)
from app.services.message import notify
from app.services.todo import create as create_todo


def apply_test_clock(raw: Optional[str]) -> None:
    """只有 test 环境接受 ims.test.now。其他环境带这个参数 → 1001。"""
    if raw is None or str(raw).strip() == "":
        return
    if get_settings().env != "test":
        raise BizError(1001, msg="不允许指定当前时间")
    moment = parse_datetime(str(raw))
    from app.core.clock import set_clock
    set_clock(lambda: moment)


@job
def scan_cert_expire() -> dict:
    """扫描有效和即将到期的证件。手动扫描与定时任务都走这里。"""
    session = get_db_session()
    rows = session.execute(
        base_stmt(MasterCert).where(MasterCert.status.in_(("EFFECTIVE", "EXPIRING")))
    ).scalars().all()
    notified = 0
    for row in rows:
        if not row.expire_date:
            continue
        days = (row.expire_date - get_now().date()).days
        level = _level(days)
        if level is None:
            continue
        if level == "LOCKED":
            row.status = "EXPIRED"
            row.warn_level = "LOCKED"
        elif level == "RED":
            row.status = "EXPIRING"
            row.warn_level = "RED"
        else:
            row.status = "EXPIRING"
            row.warn_level = "YELLOW"
        task = _task_for(row.id, level)
        if level in _split(task.notified_levels):
            continue
        task.notified_levels = ",".join([*(_split(task.notified_levels)), level])
        task.level = level
        task.status = "LOCKED" if level == "LOCKED" else "WARNING"
        _deliver(row, level)
        notified += 1
    session.flush()
    return {"notified": notified}


class CertExpireService:
    def list_expire_tasks(self, page_no: int = 1, page_size: int = 20) -> dict:
        total, rows = fetch_page(base_stmt(CertExpireTask), CertExpireTask, page_no, page_size)
        return {
            "list": [
                {
                    "id": as_text_id(row.id),
                    "certId": as_text_id(row.cert_id),
                    "level": row.level,
                    "status": row.status,
                    "remindCount": row.remind_count,
                }
                for row in rows
            ],
            "total": total,
        }

    def expire_stats(self) -> dict:
        rows = get_db_session().execute(base_stmt(CertExpireTask)).scalars().all()
        stats = {"YELLOW": 0, "RED": 0, "LOCKED": 0}
        for row in rows:
            if row.level in stats and row.status != "RENEW_RESOLVED":
                stats[row.level] += 1
        return stats

    def renew_cert(self, task_id: Any, payload: dict, filename: str, content_type: str, content: bytes) -> dict:
        ensure_write_scope()
        task = get_alive(CertExpireTask, task_id)
        old = get_alive(MasterCert, task.cert_id)
        payload = dict(payload)
        payload["renew_from_id"] = old.id
        payload.setdefault("holder_type", old.holder_type)
        payload.setdefault("holderType", old.holder_type)
        payload.setdefault("cert_type", old.cert_type)
        payload.setdefault("certType", old.cert_type)
        payload.setdefault("realname_id", old.realname_id)
        payload.setdefault("holder_user_id", old.holder_user_id)
        payload.setdefault("holder_name", old.holder_name)
        new_type = payload.get("cert_type") or payload.get("certType")
        new_holder = payload.get("holder_type") or payload.get("holderType")
        if new_type != old.cert_type or new_holder != old.holder_type:
            raise BizError(1001, msg="换证的持有人或类型与旧证不同")
        if payload.get("realname_id") not in (None, old.realname_id) and int(payload.get("realname_id") or 0) != int(old.realname_id or 0):
            raise BizError(1001, msg="换证的持有人或类型与旧证不同")
        created = CertService().upload_cert(payload, filename, content_type, content)
        return created

    def remind_expire(self, task_id: Any) -> dict:
        ensure_write_scope()
        task = get_alive(CertExpireTask, task_id)
        if task.status != "WARNING":
            raise BizError(1001, msg="预警任务已解除")
        if task.last_remind_time is not None:
            delta = get_now().replace(tzinfo=None) - task.last_remind_time
            if delta < timedelta(minutes=10):
                return {"reminded": False, "remindCount": task.remind_count}
        cert = get_alive(MasterCert, task.cert_id)
        _deliver(cert, task.level or "YELLOW", biz_key=f"{cert.id}:remind:{int(task.remind_count or 0)}")
        task.remind_count = int(task.remind_count or 0) + 1
        task.last_remind_time = get_now().replace(tzinfo=None)
        get_db_session().flush()
        return {"reminded": True, "remindCount": task.remind_count}

    def scan(self, test_now: Optional[str] = None) -> dict:
        apply_test_clock(test_now)
        return scan_cert_expire()


def _level(days: int) -> Optional[str]:
    if days <= 0:
        return "LOCKED"
    if days <= 7:
        return "RED"
    if days <= 30:
        return "YELLOW"
    return None


def _split(text: str) -> list[str]:
    return [item for item in (text or "").split(",") if item]


def _task_for(cert_id: int, level: str) -> CertExpireTask:
    session = get_db_session()
    row = session.execute(
        base_stmt(CertExpireTask).where(CertExpireTask.cert_id == cert_id)
    ).scalars().first()
    if row is not None:
        return row
    created = CertExpireTask(cert_id=cert_id, level=level, status="WARNING", notified_levels="")
    return add_row(session, created)


def _deliver(cert: MasterCert, level: str, biz_key: Optional[str] = None) -> None:
    """走 B3 的 notify / create。同一级别共用 biz_key，升级或催办换 key 才会再发。"""
    receivers = _recipients(cert)
    if not receivers:
        return
    title = f"证件到期{level}"
    session = get_db_session()
    notify(
        session,
        event_type="CERT_EXPIRE",
        biz_key=biz_key or f"{cert.id}:{level}",
        receivers=receivers,
        title=title,
        content=cert.name or "",
        source_module="公司资源",
        ref_type="CERT",
        ref_id=cert.id,
    )
    create_todo(
        session,
        todo_type="WARNING",
        source_module="公司资源",
        source_type="CERT_EXPIRE",
        source_id=int(cert.id),
        title=title,
        assignee_user_ids=receivers,
    )
    session.flush()


def _recipients(cert: MasterCert) -> list[int]:
    """有续期权限且证件范围覆盖的人，再加上在职实名人关联用户。"""
    session = get_db_session()
    found: set[int] = set()
    rows = session.query(User, Role).join(UserRole, UserRole.user_id == User.id).join(
        Role, Role.id == UserRole.role_id
    ).join(RoleMenu, RoleMenu.role_id == Role.id).join(
        Menu, Menu.id == RoleMenu.menu_id
    ).filter(
        Menu.perm_code == "ims:cert:expire:renew",
        Menu.deleted == 0,
        Role.deleted == 0,
        Role.status == "ENABLED",
        User.deleted == 0,
        User.tenant_id == tenant_id(),
    ).all()
    grouped: dict[int, set[str]] = {}
    for user, role in rows:
        grouped.setdefault(int(user.id), set()).add(role.data_scope or "")
    for uid, scopes in grouped.items():
        codes = _perm_codes(uid)
        codes.add("ims:cert:expire:renew")
        if cert_visible_for(cert, uid, codes, scopes):
            found.add(uid)
    if cert.realname_id:
        person = session.execute(
            base_stmt(MasterRealname).where(MasterRealname.id == cert.realname_id)
        ).scalars().first()
        if person and person.user_id and person.status == "ON_JOB" and person.deleted == 0:
            found.add(int(person.user_id))
    return sorted(found)


def locked_state(realname_id: int) -> bool:
    return cert_is_locked(realname_id)


def _perm_codes(user_id: int) -> set[str]:
    """该用户已启用角色上的权限码。"""
    session = get_db_session()
    rows = session.query(Menu.perm_code).join(RoleMenu, RoleMenu.menu_id == Menu.id).join(
        Role, Role.id == RoleMenu.role_id
    ).join(UserRole, UserRole.role_id == Role.id).filter(
        UserRole.user_id == user_id,
        Menu.deleted == 0,
        Menu.status == "ENABLED",
        Role.deleted == 0,
        Role.status == "ENABLED",
    ).all()
    return {item[0] for item in rows if item[0]}
