# 实名人服务（B5 FP-B5-RN）。版本 v1.0 · 2026-10-13
"""SELF 归属 user_id。在职口径是状态为 ON_JOB 且 deleted == 0。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select

from app.core.cache import Cache
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.corp.models import RealnameIntermediary
from app.domains.shared.models import AccountPersonal, MasterCert, MasterRealname, MasterSimCard
from app.domains.sys.models import User
from app.services.corp_support import (
    ID_CARD,
    REALNAME_STATUS,
    add_row,
    as_text_id,
    base_stmt,
    ensure_write_scope,
    fetch_page,
    get_alive,
    hash_field,
    masked_id,
    masked_phone,
    money_text,
    owner_filter,
    require_dict,
    require_owner_row,
    soft_delete,
    store_secret,
    valid_id_card,
    valid_mobile,
)

COMMISSION = "ims:corp:realname:commission"


class RealnameService:
    def page_realnames(self, name: str = "", id_card: str = "", page_no: int = 1, page_size: int = 20) -> dict:
        stmt = base_stmt(MasterRealname)
        clause = owner_filter(MasterRealname, "user_id")
        if clause is not None:
            stmt = stmt.where(clause)
        if name:
            stmt = stmt.where(MasterRealname.name.contains(name))
        if id_card:
            stmt = stmt.where(MasterRealname.id_card_hash == hash_field(id_card))
        total, rows = fetch_page(stmt, MasterRealname, page_no, page_size)
        counts = self._intermediary_counts([row.id for row in rows])
        return {
            "list": [self.to_realname_view(row, counts.get(row.id, 0), with_people=False) for row in rows],
            "total": total,
        }

    def get_realname(self, realname_id: Any) -> dict:
        row = require_owner_row(MasterRealname, realname_id, "user_id")
        return self.to_realname_view(row, 0, with_people=True)

    def create_realname(self, payload: dict) -> dict:
        ensure_write_scope()
        row = MasterRealname(name=self._name(payload), status="ON_JOB")
        self._fill(row, payload, creating=True)
        add_row(get_db_session(), row)
        return self.get_realname(row.id)

    def update_realname(self, realname_id: Any, payload: dict) -> dict:
        ensure_write_scope()
        row = require_owner_row(MasterRealname, realname_id, "user_id")
        if "name" in payload:
            row.name = self._name(payload)
        self._fill(row, payload, creating=False)
        get_db_session().flush()
        return self.get_realname(row.id)

    def set_realname_status(self, realname_id: Any, status: str) -> dict:
        ensure_write_scope()
        require_dict("dict_realname_status", status)
        row = require_owner_row(MasterRealname, realname_id, "user_id")
        row.status = status
        get_db_session().flush()
        return self.get_realname(row.id)

    def delete_realname(self, realname_id: Any) -> None:
        ensure_write_scope()
        row = require_owner_row(MasterRealname, realname_id, "user_id")
        refs = self._refs(row.id)
        if refs:
            raise BizError(1502, msg="关联的实体已被其他记录引用", data={"refs": refs})
        session = get_db_session()
        people = session.execute(
            base_stmt(RealnameIntermediary).where(RealnameIntermediary.realname_id == row.id)
        ).scalars().all()
        for person in people:
            soft_delete(person)
        soft_delete(row)
        session.flush()

    def create_intermediary(self, realname_id: Any, payload: dict) -> dict:
        ensure_write_scope()
        owner = require_owner_row(MasterRealname, realname_id, "user_id")
        row = self._intermediary_row(owner.id, payload)
        add_row(get_db_session(), row)
        return self._person_view(row)

    def update_intermediary(self, intermediary_id: Any, payload: dict) -> dict:
        ensure_write_scope()
        row = get_alive(RealnameIntermediary, intermediary_id)
        require_owner_row(MasterRealname, row.realname_id, "user_id")
        if "name" in payload:
            row.name = (payload.get("name") or "").strip() or row.name
        if payload.get("phone"):
            self._phone(payload.get("phone"))
            enc, digest = store_secret(payload.get("phone"))
            row.phone_enc = enc
            row.phone_hash = digest
        if "wechat" in payload:
            row.wechat = payload.get("wechat") or None
        if "relation_type" in payload or "relationType" in payload:
            row.relation_type = payload.get("relation_type") or payload.get("relationType") or row.relation_type
        if "commission_rate" in payload or "commissionRate" in payload:
            row.commission_rate = self._rate(payload.get("commission_rate", payload.get("commissionRate")))
        if "remark" in payload:
            row.remark = payload.get("remark") or None
        get_db_session().flush()
        return self._person_view(row)

    def delete_intermediary(self, intermediary_id: Any) -> None:
        ensure_write_scope()
        row = get_alive(RealnameIntermediary, intermediary_id)
        require_owner_row(MasterRealname, row.realname_id, "user_id")
        soft_delete(row)
        get_db_session().flush()

    def list_realname_options(self, keyword: str = "") -> list[dict]:
        """在职且未删除，最多 50。离职不出现。"""
        stmt = base_stmt(MasterRealname).where(MasterRealname.status == "ON_JOB")
        if keyword:
            stmt = stmt.where(MasterRealname.name.contains(keyword))
        rows = get_db_session().execute(stmt.order_by(MasterRealname.id.desc()).limit(50)).scalars().all()
        return [
            {"id": as_text_id(row.id), "name": row.name, "phone": masked_phone(row.phone_enc)}
            for row in rows
        ]

    def export_realnames(self, name: str = "") -> dict:
        """导出不带佣金列。"""
        page = self.page_realnames(name=name, page_no=1, page_size=100)
        rows = []
        for item in page["list"]:
            item.pop("commissionRate", None)
            people = item.get("intermediaries") or []
            for person in people:
                person.pop("commissionRate", None)
            rows.append(item)
        task_id = uuid4().hex
        Cache.set_json(f"ims:export:{task_id}", {"total": page["total"], "rows": rows}, ttl=3600)
        return {"taskId": task_id}

    def to_realname_view(self, row: MasterRealname, extra_count: int, with_people: bool) -> dict:
        data = {
            "id": as_text_id(row.id),
            "name": row.name,
            "userId": as_text_id(row.user_id) if row.user_id else "",
            "idType": row.id_type or "",
            "idCard": masked_id(row.id_card_enc),
            "phone": masked_phone(row.phone_enc),
            "wechat": row.wechat or "",
            "gender": row.gender or "",
            "status": REALNAME_STATUS.get(row.status, row.status),
            "statusCode": row.status,
            "intermediaryCount": extra_count,
            "intermediaryText": f"等 {extra_count} 人" if extra_count else "",
        }
        if with_people:
            people = get_db_session().execute(
                base_stmt(RealnameIntermediary).where(RealnameIntermediary.realname_id == row.id)
            ).scalars().all()
            data["intermediaries"] = [self._person_view(item) for item in people]
            data["intermediaryCount"] = len(people)
            data["intermediaryText"] = f"等 {len(people)} 人" if people else ""
        if not self._can_see_commission():
            data.pop("commissionRate", None)
            for person in data.get("intermediaries") or []:
                person.pop("commissionRate", None)
        return data

    def assert_realname_active(self, realname_id: Any) -> MasterRealname:
        """不存在 1500，离职 1501。"""
        try:
            number = int(realname_id)
        except (TypeError, ValueError) as err:
            raise BizError(1500) from err
        row = get_db_session().execute(
            base_stmt(MasterRealname).where(MasterRealname.id == number)
        ).scalars().first()
        if row is None:
            raise BizError(1500)
        if row.status != "ON_JOB":
            raise BizError(1501)
        return row

    def _fill(self, row: MasterRealname, payload: dict, creating: bool) -> None:
        if "user_id" in payload or "userId" in payload or creating:
            raw = payload.get("user_id", payload.get("userId"))
            if raw not in (None, ""):
                self._user(raw)
                row.user_id = int(raw)
        id_type = payload.get("id_type", payload.get("idType", row.id_type))
        if "id_type" in payload or "idType" in payload or (creating and id_type):
            require_dict("dict_id_type", id_type)
            row.id_type = id_type or None
        change_card = creating or payload.get("change_id_card") or payload.get("changeIdCard")
        plain = payload.get("id_card") or payload.get("idCard")
        if change_card and plain:
            self._check_card(row.id_type, plain)
            self._unique_card(plain, row.id if row.id else None)
            enc, digest = store_secret(plain)
            row.id_card_enc = enc
            row.id_card_hash = digest
        phone = payload.get("phone")
        if phone:
            if not valid_mobile(str(phone)):
                raise BizError(1001, msg="手机号格式不正确")
            enc, digest = store_secret(str(phone))
            row.phone_enc = enc
            row.phone_hash = digest
        if "wechat" in payload:
            row.wechat = payload.get("wechat") or None
        if "gender" in payload:
            row.gender = payload.get("gender") or None

    def _person_view(self, row: RealnameIntermediary) -> dict:
        data = {
            "id": as_text_id(row.id),
            "realnameId": as_text_id(row.realname_id),
            "name": row.name,
            "phone": masked_phone(row.phone_enc),
            "wechat": row.wechat or "",
            "relationType": row.relation_type,
            "remark": row.remark or "",
        }
        if self._can_see_commission():
            data["commissionRate"] = money_text(row.commission_rate)
        return data

    def _can_see_commission(self) -> bool:
        current = ctx.current_or_none
        return current is not None and COMMISSION in current.perm_codes

    def _intermediary_counts(self, ids: list[int]) -> dict[int, int]:
        if not ids:
            return {}
        session = get_db_session()
        rows = session.execute(
            select(RealnameIntermediary.realname_id, func.count())
            .where(
                RealnameIntermediary.realname_id.in_(ids),
                RealnameIntermediary.deleted == 0,
            )
            .group_by(RealnameIntermediary.realname_id)
        ).all()
        return {int(item[0]): int(item[1]) for item in rows}

    def _refs(self, realname_id: int) -> list[dict]:
        session = get_db_session()
        refs = []
        sim_count = session.execute(
            select(func.count()).select_from(MasterSimCard).where(
                MasterSimCard.realname_id == realname_id,
                MasterSimCard.deleted == 0,
            )
        ).scalar() or 0
        cert_count = session.execute(
            select(func.count()).select_from(MasterCert).where(
                MasterCert.realname_id == realname_id,
                MasterCert.deleted == 0,
            )
        ).scalar() or 0
        account_count = session.execute(
            select(func.count()).select_from(AccountPersonal).where(
                AccountPersonal.realname_id == realname_id,
                AccountPersonal.deleted == 0,
            )
        ).scalar() or 0
        if sim_count:
            refs.append({"type": "sim", "count": int(sim_count)})
        if cert_count:
            refs.append({"type": "cert", "count": int(cert_count)})
        if account_count:
            refs.append({"type": "account", "count": int(account_count)})
        return refs

    def _intermediary_row(self, realname_id: int, payload: dict) -> RealnameIntermediary:
        name = (payload.get("name") or "").strip()
        if not name:
            raise BizError(1001, msg="中介人姓名不能为空")
        phone = payload.get("phone")
        enc, digest = (None, None)
        if phone:
            self._phone(phone)
            enc, digest = store_secret(str(phone))
        return RealnameIntermediary(
            realname_id=realname_id,
            name=name,
            phone_enc=enc,
            phone_hash=digest,
            wechat=payload.get("wechat") or None,
            relation_type=payload.get("relation_type") or payload.get("relationType") or "DIRECT",
            commission_rate=self._rate(payload.get("commission_rate", payload.get("commissionRate"))),
            remark=payload.get("remark") or None,
        )

    def _name(self, payload: dict) -> str:
        text = (payload.get("name") or "").strip()
        if not text:
            raise BizError(1001, msg="姓名不能为空")
        return text

    def _user(self, raw: Any) -> None:
        try:
            number = int(raw)
        except (TypeError, ValueError) as err:
            raise BizError(1500) from err
        row = get_db_session().execute(base_stmt(User).where(User.id == number)).scalars().first()
        if row is None:
            raise BizError(1500)

    def _check_card(self, id_type: Optional[str], plain: str) -> None:
        if id_type == ID_CARD and not valid_id_card(plain):
            raise BizError(1001, msg="身份证校验位不正确")

    def _unique_card(self, plain: str, current_id: Optional[int]) -> None:
        digest = hash_field(plain)
        stmt = base_stmt(MasterRealname).where(MasterRealname.id_card_hash == digest)
        if current_id:
            stmt = stmt.where(MasterRealname.id != current_id)
        if get_db_session().execute(stmt).scalars().first() is not None:
            raise BizError(1001, msg="证件号已存在")

    def _phone(self, phone: Any) -> None:
        if not valid_mobile(str(phone)):
            raise BizError(1001, msg="手机号格式不正确")

    def _rate(self, value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        return Decimal(str(value))
