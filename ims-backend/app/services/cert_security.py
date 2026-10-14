# 证件分级与审计（B5 FP-B5-SC）。版本 v1.0 · 2026-10-13
"""查看级别、签名预览、查看日志和风险报告。"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select

from app.core.cache import Cache
from app.core.clock import format_datetime, get_now, parse_datetime
from app.core.context import ctx
from app.core.crypto import decrypt_field
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.corp.models import CertL3Whitelist, CertLevelRule, CertViewLog
from app.domains.sys.models import User
from app.services.cert_file import apply_watermark
from app.services.corp_support import as_text_id, base_stmt, ensure_write_scope, fetch_page, user_id
from app.services.operate import audit_sensitive_view

CONFIG = "ims:cert:security:config"
PREVIEW_PREFIX = "ims:cert:preview:"


def resolve_view_level(viewer_id: Optional[int] = None) -> int:
    """白名单为 3，否则取角色规则最大值，都没有则 1。"""
    current = ctx.current_or_none
    viewer = int(viewer_id if viewer_id is not None else user_id())
    session = get_db_session()
    listed = session.execute(
        base_stmt(CertL3Whitelist).where(CertL3Whitelist.user_id == viewer)
    ).scalars().first()
    if listed is not None:
        return 3
    role_ids = []
    if current is not None:
        for item in current.data_scopes:
            role_id = item.get("role_id") if isinstance(item, dict) else getattr(item, "role_id", None)
            if role_id:
                role_ids.append(int(role_id))
    if not role_ids:
        return 1
    levels = session.execute(
        select(CertLevelRule.view_level).where(
            CertLevelRule.role_id.in_(role_ids),
            CertLevelRule.deleted == 0,
        )
    ).scalars().all()
    if not levels:
        return 1
    return max(int(item) for item in levels)


def build_watermark_text(viewer_id: Optional[int] = None) -> str:
    """工号、姓名、当前时间。"""
    viewer = int(viewer_id if viewer_id is not None else user_id())
    user = get_db_session().execute(base_stmt(User).where(User.id == viewer)).scalars().first()
    emp = user.emp_no if user and user.emp_no else ""
    name = user.nickname if user else ""
    return f"{emp} {name} {format_datetime(get_now())}".strip()


def sign_preview_url(file_key: str) -> str:
    """60 秒签名。过期用 get_now 判断，不靠缓存自己的时钟。"""
    token = uuid4().hex
    expire = get_now() + timedelta(seconds=60)
    Cache.set_json(
        f"{PREVIEW_PREFIX}{token}",
        {"fileKey": file_key, "expireAt": expire.isoformat()},
        ttl=120,
    )
    return f"/admin-api/ims/cert/security/preview/{token}"


def resolve_preview(token: str) -> dict:
    data = Cache.get_json(f"{PREVIEW_PREFIX}{token}")
    if not isinstance(data, dict):
        raise BizError(1001, msg="预览地址无效")
    expire = parse_datetime(str(data.get("expireAt")))
    if get_now() > expire:
        raise BizError(1001, msg="预览地址已过期")
    return data


def count_views_in_last_hour(viewer_id: Optional[int] = None) -> int:
    """近 1 小时查看次数，含被拒绝的记录。"""
    viewer = int(viewer_id if viewer_id is not None else user_id())
    since = (get_now() - timedelta(hours=1)).replace(tzinfo=None)
    total = get_db_session().execute(
        select(func.count()).select_from(CertViewLog).where(
            CertViewLog.viewer_user_id == viewer,
            CertViewLog.deleted == 0,
            CertViewLog.view_time >= since,
        )
    ).scalar() or 0
    return int(total)


def write_view_log(cert_id: int, level: int, result: str, watermark: str = "") -> None:
    """日志失败不影响查看结果。"""
    current = ctx.current_or_none

    def _write() -> None:
        row = CertViewLog(
            cert_id=cert_id,
            viewer_user_id=user_id(),
            view_level=level,
            watermark_text=watermark or None,
            view_duration=None,
            ip=current.client_ip if current else "",
            device=(current.user_agent[:200] if current and current.user_agent else ""),
            result=result,
            view_time=get_now().replace(tzinfo=None),
        )
        from app.services.corp_support import add_row
        add_row(get_db_session(), row)

    audit_sensitive_view(_write)


def watermarked_bytes(content: bytes, text: str) -> bytes:
    return apply_watermark(content, text)


def plain_cert_no(enc: Optional[str]) -> str:
    if not enc:
        return ""
    return decrypt_field(enc)


class CertSecurityService:
    def get_level_config(self) -> dict:
        session = get_db_session()
        rules = session.execute(base_stmt(CertLevelRule)).scalars().all()
        people = session.execute(base_stmt(CertL3Whitelist)).scalars().all()
        return {
            "rules": [
                {"roleId": as_text_id(item.role_id), "viewLevel": item.view_level}
                for item in rules
            ],
            "whitelist": [as_text_id(item.user_id) for item in people],
        }

    def save_level_config(self, payload: dict) -> dict:
        """没有配置权限 → 1008。保存后下一笔查看即生效，不递增 perm_ver。"""
        current = ctx.current_or_none
        if current is None or CONFIG not in current.perm_codes:
            raise BizError(1008)
        ensure_write_scope()
        session = get_db_session()
        for row in session.execute(base_stmt(CertLevelRule)).scalars().all():
            row.deleted = row.id
        for row in session.execute(base_stmt(CertL3Whitelist)).scalars().all():
            row.deleted = row.id
        session.flush()
        for item in payload.get("rules") or []:
            role_id = int(item.get("role_id") or item.get("roleId"))
            level = int(item.get("view_level") or item.get("viewLevel") or 1)
            if level not in (1, 2, 3):
                raise BizError(1001, msg="查看级别只能是 1、2、3")
            from app.services.corp_support import add_row
            add_row(session, CertLevelRule(role_id=role_id, view_level=level))
        for raw in payload.get("whitelist") or []:
            from app.services.corp_support import add_row
            add_row(session, CertL3Whitelist(user_id=int(raw)))
        return self.get_level_config()

    def list_view_logs(self, page_no: int = 1, page_size: int = 20) -> dict:
        total, rows = fetch_page(base_stmt(CertViewLog), CertViewLog, page_no, page_size)
        return {
            "list": [
                {
                    "id": as_text_id(row.id),
                    "certId": as_text_id(row.cert_id),
                    "viewerUserId": as_text_id(row.viewer_user_id),
                    "viewLevel": row.view_level,
                    "result": row.result,
                    "watermarkText": row.watermark_text or "",
                }
                for row in rows
            ],
            "total": total,
        }

    def risk_report(self) -> dict:
        """近 1 小时查看次数大于 10 的用户。"""
        since = (get_now() - timedelta(hours=1)).replace(tzinfo=None)
        rows = get_db_session().execute(
            select(CertViewLog.viewer_user_id, func.count())
            .where(CertViewLog.deleted == 0, CertViewLog.view_time >= since)
            .group_by(CertViewLog.viewer_user_id)
        ).all()
        hot = [
            {"userId": as_text_id(item[0]), "count": int(item[1])}
            for item in rows
            if int(item[1]) > 10
        ]
        return {"users": hot}
