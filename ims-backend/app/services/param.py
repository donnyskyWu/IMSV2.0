# app/services/param.py - System parameter updates (FP-B07-02)
"""Update builtin parameters. Keys cannot be created or deleted here."""

from typing import Any

from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session

SECRET_MASK = "******"


class ParamService:
    """Read and update ``ims_sys_param`` values."""

    def display_value(self, param: Any) -> str:
        if param.value_type == "SECRET":
            return SECRET_MASK
        return param.value or ""

    def update_value(self, param_key: str, value: str) -> None:
        """Update one parameter. Unknown key -> 1213."""
        from app.domains.sys.models import Role, SysParam

        session = get_db_session()
        param = session.query(SysParam).filter(
            SysParam.param_key == param_key,
            SysParam.deleted == 0,
        ).first()
        if param is None:
            raise BizError(1213)

        if param.value_type == "SECRET" and (value is None or value == ""):
            return

        if param.value_type == "NUMBER":
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise BizError(1001, msg="参数必须是数字") from exc
            low = float(param.min_value) if param.min_value not in (None, "") else None
            high = float(param.max_value) if param.max_value not in (None, "") else None
            if (low is not None and number < low) or (high is not None and number > high):
                raise BizError(1001, msg="参数超出范围")

        if param.value_type == "ROLE_REF":
            role = session.query(Role).filter(
                Role.id == int(value),
                Role.tenant_id == ctx.tenant_id,
                Role.deleted == 0,
            ).first()
            if role is None:
                raise BizError(1500)

        param.value = value
        session.flush()
