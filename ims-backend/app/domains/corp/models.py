# 公司资源本批新建表（B5 0.5）。
"""扩容记录、中介人、到期任务、分级规则、查看日志。"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase


class OrgCompanyExpansion(AuditBase):
    """公司扩容记录。用子表，不用 JSON 列。"""

    __tablename__ = "ims_org_company_expansion"

    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    from_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    to_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    operator_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    operate_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RealnameIntermediary(AuditBase):
    """实名人名下中介人。"""

    __tablename__ = "ims_master_realname_intermediary"

    realname_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    phone_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    wechat: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="DIRECT")
    commission_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class CertExpireTask(AuditBase):
    """证件到期预警任务。"""

    __tablename__ = "ims_cert_expire_task"

    cert_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="YELLOW")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="WARNING")
    notified_levels: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_remind_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    remind_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CertLevelRule(AuditBase):
    """按角色配置的原图查看级别。"""

    __tablename__ = "ims_cert_level_rule"

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    view_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CertL3Whitelist(AuditBase):
    """L3 白名单，只允许 R1 维护。"""

    __tablename__ = "ims_cert_l3_whitelist"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class CertViewLog(AuditBase):
    """原图查看日志。view_duration 本批留空。"""

    __tablename__ = "ims_cert_view_log"

    cert_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    viewer_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    view_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    watermark_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    view_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    result: Mapped[str] = mapped_column(String(30), nullable=False, default="OK")
    view_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
