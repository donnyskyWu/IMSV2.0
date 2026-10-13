# 证件档案（B5 FP-B5-CT）。版本 v1.0 · 2026-10-13
"""证件不挂 scope_model。可见性由 cert_matches_scope 决定。"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import or_

from app.core.clock import get_now
from app.core.context import ctx
from app.core.crypto import encrypt_field
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.shared.models import MasterCert, MasterRealname
from app.domains.sys.models import StoredFile, User
from app.integrations.base import assert_http_url
from app.services.cert_file import apply_watermark, validate_cert_file
from app.services.cert_security import (
    build_watermark_text,
    count_views_in_last_hour,
    plain_cert_no,
    resolve_view_level,
    sign_preview_url,
    write_view_log,
)
from app.services.corp_support import (
    ID_CARD,
    ON_JOB,
    active_realname_clause,
    add_row,
    as_text_id,
    base_stmt,
    ensure_write_scope,
    fetch_page,
    get_alive,
    has_all_scope,
    masked_id,
    require_dict,
    scope_types,
    soft_delete,
    store_secret,
    tenant_id,
    user_id,
    valid_id_card,
)
from app.services.files import FileService
from app.services.message import notify
from app.services.realname import RealnameService

QUERY = "ims:cert:archive:query"
QUERY_SELF = "ims:cert:archive:query-self"
UPLOAD = "ims:cert:archive:upload"
OPEN_STATUSES = ("EFFECTIVE", "EXPIRING", "PENDING_REVIEW")
CERT_DIR = Path("/tmp/ims-cert-files")


def cert_matches_scope(stmt):
    """列表在租户过滤之后调用。只有 query-self 时即使 ALL 也只看本人。"""
    current = ctx.current_or_none
    if current is not None and current.is_system:
        return stmt
    codes = set(current.perm_codes) if current is not None else set()
    only_self = QUERY_SELF in codes and QUERY not in codes
    if only_self:
        return stmt.where(_self_condition())
    if QUERY in codes and has_all_scope():
        return stmt
    if QUERY in codes and "SELF" in scope_types():
        return stmt.where(_self_condition())
    return stmt.where(MasterCert.id == -1)


def cert_row_visible(row: MasterCert) -> bool:
    """与列表同一条件，供按 id 读取。"""
    found = get_db_session().execute(
        cert_matches_scope(base_stmt(MasterCert).where(MasterCert.id == row.id))
    ).scalars().first()
    return found is not None


def cert_visible_for(row: MasterCert, viewer_id: int, perm_codes: set[str], scopes: set[str]) -> bool:
    """给扫描接收人用，不改当前上下文。"""
    only_self = QUERY_SELF in perm_codes and QUERY not in perm_codes
    if only_self or (QUERY in perm_codes and "ALL" not in scopes and "SELF" in scopes):
        return _linked(row, viewer_id) or row.holder_user_id == viewer_id
    return bool(QUERY in perm_codes and "ALL" in scopes)


def cert_is_locked(realname_id: int) -> bool:
    """存在未删除且已过期的证件。看状态，不看 is_locked 列。"""
    row = get_db_session().execute(
        base_stmt(MasterCert).where(
            MasterCert.realname_id == int(realname_id),
            MasterCert.status == "EXPIRED",
        )
    ).scalars().first()
    return row is not None


def _self_condition():
    ids = [
        item.id
        for item in get_db_session().execute(
            base_stmt(MasterRealname).where(
                MasterRealname.user_id == user_id(),
                *active_realname_clause(MasterRealname),
            )
        ).scalars().all()
    ]
    return or_(MasterCert.realname_id.in_(ids or [-1]), MasterCert.holder_user_id == user_id())


def _linked(row: MasterCert, viewer_id: int) -> bool:
    if not row.realname_id:
        return False
    person = get_db_session().execute(
        base_stmt(MasterRealname).where(MasterRealname.id == row.realname_id)
    ).scalars().first()
    return bool(
        person
        and person.user_id == viewer_id
        and person.status == ON_JOB
        and person.deleted == 0
    )


class CertService:
    def list_certs(self, page_no: int = 1, page_size: int = 20) -> dict:
        total, rows = fetch_page(cert_matches_scope(base_stmt(MasterCert)), MasterCert, page_no, page_size)
        return {"list": [self._brief(row) for row in rows], "total": total}

    def get_cert(self, cert_id: Any) -> dict:
        row = self._visible(cert_id)
        return self._brief(row)

    def upload_cert(
        self,
        payload: dict,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> dict:
        ensure_write_scope()
        holder = self._holder(payload)
        cert_type = payload.get("cert_type") or payload.get("certType")
        require_dict("dict_cert_type", cert_type)
        cert_no = payload.get("cert_no") or payload.get("certNo") or ""
        if cert_type == ID_CARD and not valid_id_card(cert_no):
            raise BizError(1001, msg="身份证校验位不正确")
        issue = self._day(payload.get("issue_date") or payload.get("issueDate"))
        expire = self._day(payload.get("expire_date") or payload.get("expireDate"))
        if issue and expire and expire < issue:
            raise BizError(1001, msg="有效期不能早于签发日")
        renew_from = payload.get("renew_from_id") or payload.get("renewFromId")
        if not renew_from and self._open_exists(holder, cert_type):
            raise BizError(1032)
        ext = validate_cert_file(filename, content_type, content)
        saved = FileService().upload(CERT_DIR, f"cert{ext}", content, scene="cert")
        enc, digest = store_secret(cert_no)
        version = self._next_version(holder, cert_type)
        row = MasterCert(
            name=holder["name"],
            realname_id=holder["realname_id"],
            holder_type=holder["holder_type"],
            holder_user_id=holder["holder_user_id"],
            holder_name=holder["holder_name"],
            cert_type=cert_type,
            cert_no_enc=enc,
            cert_no_hash=digest,
            issue_date=issue,
            expire_date=expire,
            file_key=saved["file_key"],
            version=version,
            status="PENDING_REVIEW",
            renew_from_id=int(renew_from) if renew_from else None,
            is_locked=False,
            ocr_result=payload.get("ocr_result") or payload.get("ocrResult"),
        )
        add_row(get_db_session(), row)
        return self._brief(row)

    def review_cert(self, cert_id: Any, passed: bool, remark: str = "") -> dict:
        ensure_write_scope()
        row = get_alive(MasterCert, cert_id)
        if not cert_row_visible(row):
            raise BizError.not_found()
        if row.creator == user_id():
            raise BizError(1008)
        if row.status != "PENDING_REVIEW":
            raise BizError(1033)
        if row.renew_from_id:
            old = get_alive(MasterCert, row.renew_from_id)
            if old.holder_type != row.holder_type or old.cert_type != row.cert_type:
                raise BizError(1001, msg="换证的持有人或类型与旧证不同")
            if old.realname_id != row.realname_id or old.holder_user_id != row.holder_user_id:
                raise BizError(1001, msg="换证的持有人或类型与旧证不同")
        if not passed and not (remark or "").strip():
            raise BizError(1001, msg="拒绝必须填写原因")
        row.review_by = user_id()
        row.review_time = get_now().replace(tzinfo=None)
        row.review_remark = remark or None
        if passed:
            row.status = "EFFECTIVE"
            self.refresh_warn_level(row)
            if row.renew_from_id:
                old = get_alive(MasterCert, row.renew_from_id)
                old.status = "RECYCLED"
                self._resolve_renew_task(old.id)
        else:
            row.status = "REJECTED"
        get_db_session().flush()
        return self._brief(row)

    def delete_cert(self, cert_id: Any) -> None:
        ensure_write_scope()
        current = ctx.current_or_none
        if current is None or "ims:cert:archive:delete" not in current.perm_codes:
            raise BizError(1008)
        row = get_alive(MasterCert, cert_id)
        if not cert_row_visible(row):
            raise BizError.not_found()
        if row.is_locked:
            raise BizError(1502, msg="证件已锁定，不可删除")
        from app.services.todo import todo
        soft_delete(row)
        todo.cancel(source_type="CERT_EXPIRE", source_id=row.id)
        self._close_tasks(row.id)
        get_db_session().flush()

    def digital_metrics(self) -> dict:
        session = get_db_session()
        people = session.execute(
            base_stmt(MasterRealname).where(*active_realname_clause(MasterRealname))
        ).scalars().all()
        covered = 0
        for person in people:
            hit = session.execute(
                base_stmt(MasterCert).where(
                    MasterCert.realname_id == person.id,
                    MasterCert.cert_type == ID_CARD,
                    MasterCert.status.in_(("EFFECTIVE", "EXPIRING")),
                )
            ).scalars().first()
            if hit is not None:
                covered += 1
        total = len(people)
        rate = (covered / total * 100) if total else 0
        return {"total": total, "covered": covered, "rate": f"{rate:.2f}"}

    def recognize_cert(self, file_key: str) -> dict:
        """失败、超时、地址不是 http(s) 都返回 recognized=false，不抛新错误码。"""
        current = ctx.current_or_none
        if current is None or UPLOAD not in current.perm_codes:
            raise BizError(1008)
        stored = get_db_session().execute(
            base_stmt(StoredFile).where(StoredFile.file_key == file_key)
        ).scalars().first()
        if stored is None or stored.scene != "cert" or stored.uploader_id != user_id():
            raise BizError(1001, msg="文件不存在或不是本人上传")
        from app.core.config import get_settings
        from app.integrations.train_ai.client import TrainAIClient

        cfg = get_settings().train_ai
        if not cfg.enabled or not assert_http_url(cfg.base_url):
            return {"recognized": False}
        client = TrainAIClient(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            model=cfg.model,
            mode=cfg.mode,
        )
        try:
            found = client.recognize_image(self._file_bytes(file_key))
        except BizError as exc:
            if exc.code in (1106, 1107, 1109):
                return {"recognized": False}
            raise
        if not found.get("recognized"):
            return {"recognized": False}
        cert_no = found.get("certNo") or ""
        payload = {
            "name": found.get("name") or "",
            "certNo": encrypt_field(cert_no) if cert_no else "",
            "issueDate": found.get("issueDate") or "",
            "expireDate": found.get("expireDate") or "",
        }
        return {
            "recognized": True,
            "name": payload["name"],
            "certNo": cert_no,
            "issueDate": payload["issueDate"],
            "expireDate": payload["expireDate"],
            "ocrStored": json.dumps(payload, ensure_ascii=False),
        }

    def view_cert(self, cert_id: Any) -> dict:
        row = self._visible(cert_id)
        level = resolve_view_level()
        if row.status == "PENDING_REVIEW":
            write_view_log(row.id, level, "REJECTED_1033")
            raise BizError(1033)
        if count_views_in_last_hour() >= 10:
            write_view_log(row.id, level, "REJECTED_1035")
            self._notify_auditors(row.id)
            raise BizError(1035)
        if level <= 1:
            write_view_log(row.id, level, "REJECTED_1034")
            raise BizError(1034)
        text = build_watermark_text()
        content = self._file_bytes(row.file_key or "")
        apply_watermark(content, text)
        write_view_log(row.id, level, "OK", text)
        data = {
            "previewUrl": sign_preview_url(row.file_key or ""),
            "watermarkText": text,
            "viewLevel": level,
            "certNo": plain_cert_no(row.cert_no_enc) if level >= 3 else masked_id(row.cert_no_enc),
        }
        return data

    def refresh_warn_level(self, row: MasterCert) -> None:
        if not row.expire_date:
            row.warn_level = None
            return
        days = (row.expire_date - get_now().date()).days
        if days <= 0:
            row.status = "EXPIRED"
            row.warn_level = "LOCKED"
        elif days <= 7:
            row.status = "EXPIRING"
            row.warn_level = "RED"
        elif days <= 30:
            row.status = "EXPIRING"
            row.warn_level = "YELLOW"
        else:
            row.warn_level = None

    def _visible(self, cert_id: Any) -> MasterCert:
        row = get_alive(MasterCert, cert_id)
        if not cert_row_visible(row):
            raise BizError.not_found()
        return row

    def _brief(self, row: MasterCert) -> dict:
        return {
            "id": as_text_id(row.id),
            "name": row.name,
            "holderType": row.holder_type or "",
            "holderName": row.holder_name or "",
            "external": row.holder_type == "EXTERNAL",
            "realnameId": as_text_id(row.realname_id) if row.realname_id else "",
            "holderUserId": as_text_id(row.holder_user_id) if row.holder_user_id else "",
            "certType": row.cert_type or "",
            "certNo": masked_id(row.cert_no_enc),
            "status": row.status,
            "warnLevel": row.warn_level or "",
            "version": row.version,
            "fileKey": row.file_key or "",
            "isLocked": bool(row.is_locked),
        }

    def _holder(self, payload: dict) -> dict:
        kind = payload.get("holder_type") or payload.get("holderType")
        if kind == "REALNAME":
            person = RealnameService().assert_realname_active(payload.get("realname_id") or payload.get("realnameId"))
            return {
                "holder_type": kind,
                "realname_id": person.id,
                "holder_user_id": None,
                "holder_name": person.name,
                "name": person.name,
            }
        if kind == "USER":
            raw = payload.get("holder_user_id") or payload.get("holderUserId")
            user = get_db_session().execute(base_stmt(User).where(User.id == int(raw))).scalars().first()
            if user is None:
                raise BizError(1500)
            return {
                "holder_type": kind,
                "realname_id": None,
                "holder_user_id": user.id,
                "holder_name": user.nickname,
                "name": user.nickname,
            }
        if kind == "EXTERNAL":
            name = (payload.get("holder_name") or payload.get("holderName") or "").strip()
            if not name:
                raise BizError(1001, msg="外协持有人姓名不能为空")
            return {
                "holder_type": kind,
                "realname_id": None,
                "holder_user_id": None,
                "holder_name": name,
                "name": name,
            }
        raise BizError(1001, msg="持有人类型不正确")

    def _open_exists(self, holder: dict, cert_type: str) -> bool:
        stmt = base_stmt(MasterCert).where(
            MasterCert.cert_type == cert_type,
            MasterCert.status.in_(OPEN_STATUSES),
            MasterCert.holder_type == holder["holder_type"],
        )
        if holder["realname_id"]:
            stmt = stmt.where(MasterCert.realname_id == holder["realname_id"])
        elif holder["holder_user_id"]:
            stmt = stmt.where(MasterCert.holder_user_id == holder["holder_user_id"])
        else:
            stmt = stmt.where(MasterCert.holder_name == holder["holder_name"])
        return get_db_session().execute(stmt).scalars().first() is not None

    def _next_version(self, holder: dict, cert_type: str) -> int:
        stmt = base_stmt(MasterCert).where(MasterCert.cert_type == cert_type)
        if holder["realname_id"]:
            stmt = stmt.where(MasterCert.realname_id == holder["realname_id"])
        rows = get_db_session().execute(stmt).scalars().all()
        if not rows:
            return 1
        return max(int(item.version or 1) for item in rows) + 1

    def _day(self, value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    def _file_bytes(self, file_key: str) -> bytes:
        path = CERT_DIR / file_key
        if file_key and path.is_file():
            return path.read_bytes()
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

    def _notify_auditors(self, cert_id: int) -> None:
        from app.domains.sys.models import Menu, Role, RoleMenu, UserRole

        session = get_db_session()
        users = session.query(User.id).join(UserRole, UserRole.user_id == User.id).join(
            Role, Role.id == UserRole.role_id
        ).join(RoleMenu, RoleMenu.role_id == Role.id).join(
            Menu, Menu.id == RoleMenu.menu_id
        ).filter(
            Menu.perm_code == "ims:cert:security:audit",
            Menu.deleted == 0,
            User.deleted == 0,
            User.tenant_id == tenant_id(),
        ).all()
        for item in users:
            notify(int(item[0]), "证件高频查看", f"证件 {cert_id}", scene="CERT_VIEW")

    def _close_tasks(self, cert_id: int) -> None:
        from app.domains.corp.models import CertExpireTask
        rows = get_db_session().execute(
            base_stmt(CertExpireTask).where(CertExpireTask.cert_id == cert_id)
        ).scalars().all()
        for task in rows:
            if task.status == "WARNING":
                task.status = "EXPIRED_LOCKED"
        get_db_session().flush()

    def _resolve_renew_task(self, cert_id: int) -> None:
        from app.domains.corp.models import CertExpireTask
        from app.services.todo import todo
        rows = get_db_session().execute(
            base_stmt(CertExpireTask).where(CertExpireTask.cert_id == cert_id)
        ).scalars().all()
        for task in rows:
            task.status = "RENEW_RESOLVED"
        todo.complete(source_type="CERT_EXPIRE", source_id=cert_id)
