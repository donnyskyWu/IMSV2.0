# 手机卡服务（B5 FP-B5-SM）。版本 v1.0 · 2026-10-13
"""SELF 归属 assigned_user_id。编辑不改号码密文。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from app.core.cache import Cache
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.shared.models import MasterPhone, MasterRealname, MasterSimCard
from app.services.corp_support import (
    add_row,
    as_text_id,
    base_stmt,
    dict_label,
    ensure_write_scope,
    fetch_page,
    hash_field,
    masked_phone,
    money_text,
    owner_filter,
    require_dict,
    require_owner_row,
    soft_delete,
    store_secret,
    valid_mobile,
)
from app.services.realname import RealnameService


class SimCardService:
    def page_sim_cards(
        self,
        phone: str = "",
        operator: str = "",
        page_no: int = 1,
        page_size: int = 20,
    ) -> dict:
        stmt = base_stmt(MasterSimCard)
        clause = owner_filter(MasterSimCard, "assigned_user_id")
        if clause is not None:
            stmt = stmt.where(clause)
        if phone:
            stmt = stmt.where(MasterSimCard.phone_number_hash == hash_field(phone))
        if operator:
            stmt = stmt.where(MasterSimCard.operator == operator)
        total, rows = fetch_page(stmt, MasterSimCard, page_no, page_size)
        return {"list": [self._view(row) for row in rows], "total": total}

    def get_sim_card(self, sim_id: Any) -> dict:
        row = require_owner_row(MasterSimCard, sim_id, "assigned_user_id")
        data = self._view(row)
        data["accounts"] = []
        return data

    def create_sim_card(self, payload: dict) -> dict:
        ensure_write_scope()
        phone = str(payload.get("phone") or payload.get("phone_number") or "")
        if not valid_mobile(phone):
            raise BizError(1001, msg="手机号必须为11位")
        operator = payload.get("operator")
        require_dict("dict_sim_operator", operator)
        realname_id = payload.get("realname_id", payload.get("realnameId"))
        if not realname_id:
            raise BizError(1001, msg="实名人不能为空")
        RealnameService().assert_realname_active(realname_id)
        self._unique_phone(phone, None)
        iccid = payload.get("iccid") or None
        if iccid:
            self._unique_iccid(str(iccid), None)
        phone_enc, phone_hash = store_secret(phone)
        iccid_enc, iccid_hash = store_secret(str(iccid) if iccid else None)
        status = payload.get("status") or "ENABLED"
        require_dict("dict_sim_status", status)
        if payload.get("payment_cycle") or payload.get("paymentCycle"):
            require_dict("dict_payment_cycle", payload.get("payment_cycle") or payload.get("paymentCycle"))
        row = MasterSimCard(
            name=phone[:3] + "****" + phone[-4:],
            phone_number_enc=phone_enc,
            phone_number_hash=phone_hash,
            phone_id=None,
            realname_id=int(realname_id),
            operator=operator,
            assigned_user_id=self._optional_int(payload.get("assigned_user_id", payload.get("assignedUserId"))),
            iccid_enc=iccid_enc,
            iccid_hash=iccid_hash,
            package_name=payload.get("package_name") or payload.get("packageName"),
            monthly_rent=self._rent(payload.get("monthly_rent", payload.get("monthlyRent"))),
            activated_at=self._date(payload.get("activated_at") or payload.get("activatedAt")),
            payment_cycle=payload.get("payment_cycle") or payload.get("paymentCycle"),
            next_payment_date=self._date(payload.get("next_payment_date") or payload.get("nextPaymentDate")),
            is_primary=bool(payload.get("is_primary") or payload.get("isPrimary")),
            status=status,
        )
        add_row(get_db_session(), row)
        return self.get_sim_card(row.id)

    def update_sim_card(self, sim_id: Any, payload: dict) -> dict:
        ensure_write_scope()
        row = require_owner_row(MasterSimCard, sim_id, "assigned_user_id")
        if "operator" in payload:
            require_dict("dict_sim_operator", payload.get("operator"))
            row.operator = payload.get("operator")
        if "realname_id" in payload or "realnameId" in payload:
            realname_id = payload.get("realname_id", payload.get("realnameId"))
            RealnameService().assert_realname_active(realname_id)
            row.realname_id = int(realname_id)
        if "assigned_user_id" in payload or "assignedUserId" in payload:
            row.assigned_user_id = self._optional_int(payload.get("assigned_user_id", payload.get("assignedUserId")))
        if "iccid" in payload and payload.get("iccid"):
            self._unique_iccid(str(payload.get("iccid")), row.id)
            enc, digest = store_secret(str(payload.get("iccid")))
            row.iccid_enc = enc
            row.iccid_hash = digest
        if "package_name" in payload or "packageName" in payload:
            row.package_name = payload.get("package_name") or payload.get("packageName")
        if "monthly_rent" in payload or "monthlyRent" in payload:
            row.monthly_rent = self._rent(payload.get("monthly_rent", payload.get("monthlyRent")))
        if "status" in payload:
            require_dict("dict_sim_status", payload.get("status"))
            row.status = payload.get("status")
        if "is_primary" in payload or "isPrimary" in payload:
            row.is_primary = bool(payload.get("is_primary") if "is_primary" in payload else payload.get("isPrimary"))
        # 编辑不改号码密文，phone_id 保持空。
        get_db_session().flush()
        return self.get_sim_card(row.id)

    def delete_sim_card(self, sim_id: Any) -> None:
        ensure_write_scope()
        row = require_owner_row(MasterSimCard, sim_id, "assigned_user_id")
        used = get_db_session().execute(
            base_stmt(MasterPhone).where(MasterPhone.sim_card_id == row.id)
        ).scalars().first()
        if used is not None:
            raise BizError(1502, msg="该记录已被其他数据引用，无法操作", data={"refs": [{"type": "phone", "count": 1}]})
        soft_delete(row)
        get_db_session().flush()

    def list_sim_card_options(self, keyword: str = "") -> list[dict]:
        stmt = base_stmt(MasterSimCard).where(MasterSimCard.status == "ENABLED")
        rows = get_db_session().execute(stmt.order_by(MasterSimCard.id.desc()).limit(50)).scalars().all()
        items = [
            {"id": as_text_id(row.id), "name": row.name, "phone": masked_phone(row.phone_number_enc)}
            for row in rows
        ]
        if keyword:
            items = [item for item in items if keyword in item["name"] or keyword in item["phone"]]
        return items[:50]

    def export_sim_cards(self, phone: str = "") -> dict:
        page = self.page_sim_cards(phone=phone, page_no=1, page_size=100)
        task_id = uuid4().hex
        Cache.set_json(f"ims:export:{task_id}", page, ttl=3600)
        return {"taskId": task_id}

    def _view(self, row: MasterSimCard) -> dict:
        person = None
        if row.realname_id:
            person = get_db_session().execute(
                base_stmt(MasterRealname).where(MasterRealname.id == row.realname_id)
            ).scalars().first()
        return {
            "id": as_text_id(row.id),
            "name": row.name,
            "phone": masked_phone(row.phone_number_enc),
            "realnameId": as_text_id(row.realname_id) if row.realname_id else "",
            "realnameName": person.name if person else "",
            "operator": row.operator or "",
            "operatorLabel": dict_label("dict_sim_operator", row.operator),
            "assignedUserId": as_text_id(row.assigned_user_id) if row.assigned_user_id else "",
            "packageName": row.package_name or "",
            "monthlyRent": money_text(row.monthly_rent),
            "status": "启用" if row.status == "ENABLED" else "停用",
            "statusCode": row.status,
            "isPrimary": bool(row.is_primary),
        }

    def _unique_phone(self, phone: str, current_id: Optional[int]) -> None:
        digest = hash_field(phone)
        stmt = base_stmt(MasterSimCard).where(MasterSimCard.phone_number_hash == digest)
        if current_id:
            stmt = stmt.where(MasterSimCard.id != current_id)
        if get_db_session().execute(stmt).scalars().first() is not None:
            raise BizError(1001, msg="手机号已存在")

    def _unique_iccid(self, iccid: str, current_id: Optional[int]) -> None:
        if not iccid:
            return
        digest = hash_field(iccid)
        stmt = base_stmt(MasterSimCard).where(MasterSimCard.iccid_hash == digest)
        if current_id:
            stmt = stmt.where(MasterSimCard.id != current_id)
        if get_db_session().execute(stmt).scalars().first() is not None:
            raise BizError(1001, msg="ICCID已存在")

    def _optional_int(self, value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        return int(value)

    def _rent(self, value: Any) -> Optional[Decimal]:
        if value in (None, ""):
            return None
        return Decimal(str(value))

    def _date(self, value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return date.fromisoformat(str(value)[:10])
