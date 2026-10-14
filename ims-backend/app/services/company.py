# 公司服务（B5 FP-B5-CO）。版本 v1.0 · 2026-10-13
"""公司路由不挂 scope_model。DEPT/SELF 由 company_rows_hidden 显式返回空或 1504。"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select

from app.core.cache import Cache
from app.core.clock import get_now
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.corp.models import OrgCompanyExpansion
from app.domains.shared.models import AccountPlatform, OrgCompany
from app.services.corp_support import (
    COMPANY_STATUS,
    add_row,
    as_text_id,
    base_stmt,
    company_rows_hidden,
    fetch_page,
    get_alive,
    masked_id,
    require_dict,
    store_secret,
    tenant_id,
    user_id,
    valid_credit_code,
)

MP_PLATFORMS = ("WECHAT_OFFICIAL", "WECHAT_SERVICE")


class CompanyService:
    """公司档案。读列表和按 id 读只放行 ALL。选择器不走这道判断。"""

    def page_companies(self, name: str = "", status: str = "", page_no: int = 1, page_size: int = 20) -> dict:
        if company_rows_hidden():
            return {"list": [], "total": 0}
        stmt = self._filtered(name, status)
        total, rows = fetch_page(stmt, OrgCompany, page_no, page_size)
        return {"list": [self._brief(row) for row in rows], "total": total}

    def get_company(self, company_id: Any) -> dict:
        if company_rows_hidden():
            raise BizError.not_found()
        return self._detail(company_id)

    def _detail(self, company_id: Any) -> dict:
        row = get_alive(OrgCompany, company_id)
        data = self._brief(row)
        data["address"] = row.address or ""
        data["legalIdCard"] = masked_id(row.legal_id_card_enc)
        data["expansions"] = self._expansions(row.id)
        data["mpRegistered"] = self.count_mp_registered(row.id)
        return data

    def create_company(self, payload: dict) -> dict:
        name = self._require_name(payload.get("name"))
        credit = self._credit(payload.get("credit_code") or payload.get("creditCode"))
        industry = payload.get("industry") or None
        require_dict("dict_industry", industry)
        status = payload.get("status") or "ENABLED"
        require_dict("dict_company_status", status)
        self._unique_name(name, None)
        self._unique_credit(credit, None)
        enc, digest = store_secret(payload.get("legal_id_card") or payload.get("legalIdCard"))
        row = OrgCompany(
            name=name,
            credit_code=credit,
            industry=industry,
            address=payload.get("address") or None,
            legal_name=payload.get("legal_name") or payload.get("legalName") or None,
            legal_id_card_enc=enc,
            legal_id_card_hash=digest,
            # 新建可以带初始容量。编辑接口不改容量，之后只走扩容。
            mp_capacity=self._capacity(payload.get("mp_capacity", payload.get("mpCapacity"))),
            status=status,
        )
        add_row(get_db_session(), row)
        return self._detail(row.id)

    def update_company(self, company_id: Any, payload: dict) -> dict:
        row = get_alive(OrgCompany, company_id)
        if "name" in payload:
            name = self._require_name(payload.get("name", row.name))
            self._unique_name(name, row.id)
            row.name = name
        credit = payload.get("credit_code", payload.get("creditCode", row.credit_code))
        if "credit_code" in payload or "creditCode" in payload:
            credit = self._credit(credit)
            self._unique_credit(credit, row.id)
            row.credit_code = credit
        if "industry" in payload:
            require_dict("dict_industry", payload.get("industry"))
            row.industry = payload.get("industry") or None
        if "address" in payload:
            row.address = payload.get("address") or None
        if "legal_name" in payload or "legalName" in payload:
            row.legal_name = payload.get("legal_name") or payload.get("legalName") or None
        if payload.get("legal_id_card") or payload.get("legalIdCard"):
            enc, digest = store_secret(payload.get("legal_id_card") or payload.get("legalIdCard"))
            row.legal_id_card_enc = enc
            row.legal_id_card_hash = digest
        # 编辑不改公众号容量，容量只走扩容。
        return self._detail(row.id)

    def set_company_status(self, company_id: Any, status: str) -> dict:
        require_dict("dict_company_status", status)
        row = get_alive(OrgCompany, company_id)
        row.status = status
        get_db_session().flush()
        return self._detail(row.id)

    def expand_company(self, company_id: Any, to_capacity: Any, reason: str) -> dict:
        row = get_alive(OrgCompany, company_id)
        if reason is None or str(reason).strip() == "":
            raise BizError(1001, msg="扩容原因不能为空")
        try:
            target = int(to_capacity)
        except (TypeError, ValueError) as err:
            raise BizError(1001, msg="新容量必须为整数") from err
        registered = self.count_mp_registered(row.id)
        if registered > target:
            raise BizError(1222)
        expansion = OrgCompanyExpansion(
            company_id=row.id,
            from_capacity=row.mp_capacity or 0,
            to_capacity=target,
            reason=str(reason).strip(),
            operator_id=user_id(),
            operate_time=get_now().replace(tzinfo=None),
        )
        add_row(get_db_session(), expansion)
        row.mp_capacity = target
        get_db_session().flush()
        return self._detail(row.id)

    def list_company_options(self, keyword: str = "") -> list[dict]:
        """选择器：登录即可，不套数据范围，最多 50 条启用公司。"""
        stmt = base_stmt(OrgCompany).where(OrgCompany.status == "ENABLED")
        if keyword:
            stmt = stmt.where(OrgCompany.name.contains(keyword))
        rows = get_db_session().execute(stmt.order_by(OrgCompany.id.desc()).limit(50)).scalars().all()
        return [{"id": as_text_id(row.id), "name": row.name} for row in rows]

    def export_companies(self, name: str = "", status: str = "") -> dict:
        """异步导出：筛选与列表相同，身份证脱敏，结果放 Redis。"""
        if company_rows_hidden():
            task_id = uuid4().hex
            Cache.set_json(f"ims:export:{task_id}", {"total": 0, "rows": []}, ttl=3600)
            return {"taskId": task_id}
        total, rows = fetch_page(self._filtered(name, status), OrgCompany, 1, 100)
        payload = []
        for row in rows:
            item = self._brief(row)
            item["legalIdCard"] = masked_id(row.legal_id_card_enc)
            payload.append(item)
        task_id = uuid4().hex
        Cache.set_json(f"ims:export:{task_id}", {"total": total, "rows": payload}, ttl=3600)
        return {"taskId": task_id}

    def count_mp_registered(self, company_id: int) -> int:
        """公众号已注册数。没有登记接口，没有行时为 0。"""
        session = get_db_session()
        stmt = select(func.count()).select_from(AccountPlatform).where(
            AccountPlatform.company_id == int(company_id),
            AccountPlatform.deleted == 0,
            AccountPlatform.tenant_id == tenant_id(),
            AccountPlatform.platform.in_(MP_PLATFORMS),
        )
        return int(session.execute(stmt).scalar() or 0)

    def _filtered(self, name: str, status: str):
        stmt = base_stmt(OrgCompany)
        if name:
            stmt = stmt.where(OrgCompany.name.contains(name))
        if status:
            stmt = stmt.where(OrgCompany.status == status)
        return stmt

    def _brief(self, row: OrgCompany) -> dict:
        registered = self.count_mp_registered(row.id)
        capacity = int(row.mp_capacity or 0)
        return {
            "id": as_text_id(row.id),
            "name": row.name,
            "creditCode": row.credit_code or "",
            "industry": row.industry or "",
            "legalName": row.legal_name or "",
            "status": COMPANY_STATUS.get(row.status, row.status),
            "statusCode": row.status,
            "mpCapacity": capacity,
            "mpRegistered": registered,
            "capacityTight": (capacity - registered) < 5,
        }

    def _expansions(self, company_id: int) -> list[dict]:
        rows = get_db_session().execute(
            base_stmt(OrgCompanyExpansion).where(OrgCompanyExpansion.company_id == company_id)
        ).scalars().all()
        return [
            {
                "id": as_text_id(item.id),
                "fromCapacity": item.from_capacity,
                "toCapacity": item.to_capacity,
                "reason": item.reason,
            }
            for item in rows
        ]

    def _capacity(self, raw: Any) -> int:
        """新建时的初始容量。不传则为 0。"""
        if raw in (None, ""):
            return 0
        return int(raw)

    def _require_name(self, name: Optional[str]) -> str:
        text = (name or "").strip()
        if not text:
            raise BizError(1001, msg="公司名称不能为空")
        return text

    def _credit(self, credit: Optional[str]) -> Optional[str]:
        if credit is None or str(credit).strip() == "":
            return None
        code = str(credit).strip().upper()
        if not valid_credit_code(code):
            raise BizError(1001, msg="信用代码格式不正确")
        return code

    def _unique_name(self, name: str, current_id: Optional[int]) -> None:
        stmt = base_stmt(OrgCompany).where(OrgCompany.name == name)
        if current_id is not None:
            stmt = stmt.where(OrgCompany.id != current_id)
        if get_db_session().execute(stmt).scalars().first() is not None:
            raise BizError(1001, msg="公司名称已存在")

    def _unique_credit(self, credit: Optional[str], current_id: Optional[int]) -> None:
        if not credit:
            return
        stmt = base_stmt(OrgCompany).where(OrgCompany.credit_code == credit)
        if current_id is not None:
            stmt = stmt.where(OrgCompany.id != current_id)
        if get_db_session().execute(stmt).scalars().first() is not None:
            raise BizError(1001, msg="信用代码已存在")
