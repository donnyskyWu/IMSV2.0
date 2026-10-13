# 公司资源共用的租户、软删、字典和数据范围谓词。
"""公司不走数据范围。实名人、手机卡按非空 owner。证件用 cert_matches_scope。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Query

from app.core.context import ctx
from app.core.crypto import encrypt_field, hash_field
from app.core.errors import BizError
from app.core.masking import mask_id_card, mask_mobile
from app.db.ids import assign_pk
from app.db.session import get_db_session

ON_JOB = "ON_JOB"
REALNAME_STATUS = {"ON_JOB": "在职", "LEFT": "离职"}
COMPANY_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}
ID_CARD = "ID_CARD"


def tenant_id() -> int:
    """当前租户。没有上下文时 1008。"""
    current = ctx.current_or_none
    if current is None or current.tenant_id is None:
        raise BizError(1008)
    return int(current.tenant_id)


def user_id() -> int:
    current = ctx.current_or_none
    if current is None or current.user_id is None:
        raise BizError(1008)
    return int(current.user_id)


def soft_delete(row: Any) -> None:
    """逻辑删除：deleted = id。"""
    row.deleted = row.id


def alive(model: Any) -> Any:
    """未删除且属于当前租户。"""
    return (model.tenant_id == tenant_id(), model.deleted == 0)


def require_dict(dict_type: str, value: Optional[str]) -> None:
    """空值跳过。有值则必须是启用的字典项，否则 1503。"""
    if not value:
        return
    from app.domains.sys.models import DictData

    session = get_db_session()
    row = session.query(DictData).filter(
        DictData.dict_type == dict_type,
        DictData.dict_value == value,
        DictData.deleted == 0,
        DictData.status == "ENABLED",
    ).first()
    if row is None:
        raise BizError(1503)


def scope_types() -> set[str]:
    current = ctx.current_or_none
    if current is None:
        return set()
    return set(current.get_data_scope_types())


def has_all_scope() -> bool:
    current = ctx.current_or_none
    return current is not None and current.has_all_data_scope()


def owner_visible(query: Query, model: Any, owner_name: str) -> Query:
    """ALL 不额外限制。只有 SELF 命中 owner。DEPT 或未配置不贡献行。"""
    if has_all_scope():
        return query
    types = scope_types()
    if "SELF" in types:
        return query.filter(getattr(model, owner_name) == user_id())
    return query.filter(model.id == -1)


def row_in_owner_scope(row: Any, owner_name: str) -> bool:
    if has_all_scope():
        return True
    types = scope_types()
    return bool("SELF" in types and getattr(row, owner_name) == user_id())


def ensure_write_scope() -> None:
    """实名人、手机卡、证件的写接口：没有数据范围 → 1008。公司不调用。"""
    current = ctx.current_or_none
    if current is None or not current.data_scopes:
        raise BizError(1008)


def store_secret(plain: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not plain:
        return None, None
    return encrypt_field(plain), hash_field(plain)


def masked_id(enc: Optional[str]) -> str:
    if not enc:
        return ""
    from app.core.crypto import decrypt_field
    return mask_id_card(decrypt_field(enc))


def masked_phone(enc: Optional[str]) -> str:
    if not enc:
        return ""
    from app.core.crypto import decrypt_field
    return mask_mobile(decrypt_field(enc))


def add_row(session: Any, row: Any) -> Any:
    row.tenant_id = tenant_id()
    assign_pk(session, row)
    session.add(row)
    session.flush()
    return row


def active_realname_clause(model: Any) -> Any:
    """在职且未删除。离职记录 deleted 仍为 0，必须看状态。"""
    return (model.status == ON_JOB, model.deleted == 0, model.tenant_id == tenant_id())


_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECK = "10X98765432"
_CREDIT_CHARS = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_CREDIT_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)


def valid_id_card(value: str) -> bool:
    """18 位居民身份证，含校验位。"""
    if not value or len(value) != 18 or not value[:17].isdigit():
        return False
    total = sum(int(ch) * weight for ch, weight in zip(value[:17], _ID_WEIGHTS, strict=False))
    return value[-1].upper() == _ID_CHECK[total % 11]


def valid_credit_code(value: str) -> bool:
    """18 位统一社会信用代码，含校验位。"""
    if not value or len(value) != 18:
        return False
    code = value.upper()
    if any(ch not in _CREDIT_CHARS for ch in code):
        return False
    total = sum(_CREDIT_CHARS.index(ch) * weight for ch, weight in zip(code[:17], _CREDIT_WEIGHTS, strict=False))
    expect = _CREDIT_CHARS[(31 - total % 31) % 31]
    return code[-1] == expect


def valid_mobile(value: str) -> bool:
    """11 位手机号。"""
    return bool(value) and len(value) == 11 and value.isdigit() and value.startswith("1")


def owner_filter(model: Any, owner_name: str) -> Any:
    """给 Select 用的归属条件。ALL 返回 None，表示不额外限制。"""
    if has_all_scope():
        return None
    if "SELF" in scope_types():
        return getattr(model, owner_name) == user_id()
    return model.id == -1


def as_text_id(value: Any) -> str:
    """接口里的 id 一律字符串。"""
    if value is None:
        return ""
    return str(value)


def money_text(value: Any) -> str:
    """金额两位小数字符串，不做分换算。"""
    if value is None or value == "":
        return "0.00"
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def fetch_page(stmt: Any, model: Any, page_no: int = 1, page_size: int = 20) -> tuple[int, list]:
    """按创建时间、id 倒序分页。默认 20 条。"""
    from sqlalchemy import func, select

    session = get_db_session()
    page_no = max(int(page_no or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    ordered = stmt.order_by(model.create_time.desc(), model.id.desc())
    rows = session.execute(ordered.offset((page_no - 1) * page_size).limit(page_size)).scalars().all()
    return int(total), list(rows)


def base_stmt(model: Any) -> Any:
    """租户 + 未删除。不在业务里手写 tenant_id。"""
    from app.db.repository import BaseRepository
    return BaseRepository(model)._base_query()


def get_alive(model: Any, pk: Any) -> Any:
    """按 id 取本租户未删除行。没有则 1504，响应不带名称。"""
    session = get_db_session()
    try:
        number = int(pk)
    except (TypeError, ValueError) as err:
        raise BizError.not_found() from err
    row = session.execute(base_stmt(model).where(model.id == number)).scalars().first()
    if row is None:
        raise BizError.not_found()
    return row


def require_owner_row(model: Any, pk: Any, owner_name: str) -> Any:
    """按 id 读取后再套与列表相同的归属条件。"""
    row = get_alive(model, pk)
    if not row_in_owner_scope(row, owner_name):
        raise BizError.not_found()
    return row
