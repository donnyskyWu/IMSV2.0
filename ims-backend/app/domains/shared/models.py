# app/domains/shared/models.py - Shared entity skeleton (FP-B05-01)
"""
Twelve shared entity tables reserved by B0a.

Column ``football_room_id`` on the session table is an external reference.
The Football table name is not used in this module.
"""

from typing import Optional

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase


class _Named(AuditBase):
    __abstract__ = True

    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")


class OrgCompany(_Named):
    __tablename__ = "ims_org_company"


class MasterRealname(_Named):
    __tablename__ = "ims_master_realname"

    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class MasterSimCard(_Named):
    __tablename__ = "ims_master_sim_card"


class MasterPhone(_Named):
    __tablename__ = "ims_master_phone"

    sim_card_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class MasterCert(_Named):
    __tablename__ = "ims_master_cert"

    realname_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class AccountPlatform(_Named):
    __tablename__ = "ims_account_platform"

    author_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


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
