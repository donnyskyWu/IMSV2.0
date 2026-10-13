# app/services/system_param.py - Parameter management service (B2-M02)
"""
Parameter management service.

Implements P-01 to P-03 from the B2 system management module:
- Parameter list
- Parameter update
- Attendance parameter group
"""

from typing import Any, Optional

from app.core.errors import BizError
from app.db.session import get_db_session
from app.db.transaction import transactional


class SystemParamService:
    """Parameter management service for B2 system management."""

    async def get_param_list(
        self,
        group: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get parameter list (P-01)."""
        from app.domains.sys.models import SysParam

        session = get_db_session()

        query = session.query(SysParam).filter(
            SysParam.deleted == 0,
        )

        if group:
            query = query.filter(SysParam.group == group)

        params = query.order_by(SysParam.id).all()

        return [
            {
                "id": str(p.id),
                "param_key": p.param_key,
                "name": p.name,
                "group": p.group,
                "value_type": p.value_type,
                "value": self._mask_value(p.value, p.value_type),
                "default_value": p.default_value,
                "min_value": p.min_value,
                "max_value": p.max_value,
                "options": p.options,
                "is_builtin": p.is_builtin,
                "remark": p.remark,
            }
            for p in params
        ]

    def _mask_value(self, value: Optional[str], value_type: str) -> Optional[str]:
        """Mask secret values."""
        if value_type == "SECRET" and value:
            return "******"
        return value

    @transactional
    async def update_param(self, param_key: str, value: str) -> dict[str, Any]:
        """Update parameter value (P-02)."""
        from app.domains.sys.models import SysParam

        session = get_db_session()

        param = session.query(SysParam).filter(
            SysParam.param_key == param_key,
            SysParam.deleted == 0,
        ).first()

        if not param:
            raise BizError(1213)

        # Validate value based on type
        if param.value_type == "NUMBER":
            try:
                num = float(value)
                if param.min_value and num < float(param.min_value):
                    raise BizError(1001, msg=f"值不能小于{param.min_value}")
                if param.max_value and num > float(param.max_value):
                    raise BizError(1001, msg=f"值不能大于{param.max_value}")
            except ValueError as exc:
                raise BizError(1001, msg="值必须是数字") from exc

        if param.value_type == "BOOLEAN" and value not in ("true", "false", "1", "0"):
            raise BizError(1001, msg="值必须是布尔值")

        if param.value_type == "ENUM" and param.options:
            import json
            options = json.loads(param.options)
            valid_values = [o.get("value") for o in options]
            if value not in valid_values:
                raise BizError(1001, msg="值不在允许的选项中")

        if param.value_type == "ROLE_REF":
            from app.domains.sys.models import Role
            role = session.query(Role).filter(
                Role.id == int(value),
                Role.deleted == 0,
            ).first()
            if not role:
                raise BizError(1500)

        param.value = value
        session.flush()

        return {
            "param_key": param.param_key,
            "value": self._mask_value(param.value, param.value_type),
        }
