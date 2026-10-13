# app/domains/shared/models.py - Shared entity skeleton (FP-B05-01)
"""
Twelve shared entity tables reserved by B0a.

Column ``football_room_id`` on the session table is an external reference.
The Football table name is not used in this module.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase


class _Named(AuditBase):
    __abstract__ = True

    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")


class OrgCompany(_Named):
    """公司。不声明数据范围字段，路由不挂 scope_model。"""

    __tablename__ = "ims_org_company"

    credit_code: Mapped[Optional[str]] = mapped_column(String(18), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_id_card_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legal_id_card_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mp_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ENABLED")


class MasterRealname(_Named):
    """实名人。SELF 归属关联员工 user_id。"""

    __tablename__ = "ims_master_realname"
    __scope_fields__ = {"owner": "user_id"}

    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    id_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    id_card_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    id_card_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    phone_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    wechat: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ON_JOB")


class MasterSimCard(_Named):
    """手机卡。SELF 归属使用人。"""

    __tablename__ = "ims_master_sim_card"
    __scope_fields__ = {"owner": "assigned_user_id"}

    phone_number_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_number_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    phone_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    realname_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assigned_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    iccid_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iccid_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    package_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    monthly_rent: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    activated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_cycle: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    next_payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ENABLED")


class MasterPhone(_Named):
    __tablename__ = "ims_master_phone"

    sim_card_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class MasterCert(_Named):
    """证件。本人条件由 cert_matches_scope 处理，不挂单列 scope_model。"""

    __tablename__ = "ims_master_cert"

    realname_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    holder_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    holder_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    holder_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cert_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cert_no_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cert_no_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_key: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_REVIEW")
    warn_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    review_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    review_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    renew_from_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ocr_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AccountPlatform(_Named):
    __tablename__ = "ims_account_platform"

    author_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # 可空外键，供容量统计。本批没有登记账号接口。
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class AccountPersonal(_Named):
    __tablename__ = "ims_account_personal"

    realname_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class IpgGroup(_Named):
    __tablename__ = "ims_ipg_group"


class IpgMember(_Named):
    __tablename__ = "ims_ipg_member"

    group_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class MasterAuthor(_Named):
    __tablename__ = "ims_master_author"

    realname_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class LiveSession(_Named):
    __tablename__ = "ims_live_session"

    session_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    author_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    football_room_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class CompAccount(_Named):
    __tablename__ = "ims_comp_account"

    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
