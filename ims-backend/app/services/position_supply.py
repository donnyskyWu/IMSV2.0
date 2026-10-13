# app/services/position_supply.py - Position to role supply (FP-D05)
"""Deliver position-change events and archive supply-rule versions."""

from typing import Any

from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.db.session import get_db_session

HOLDER_PERM = "ims:system:role:query"


class PositionSupplyService:
    """Create pending auto-roles from position changes and keep manual roles."""

    def deliver(self, event_id: str, user_id: int, position_code: str) -> dict[str, Any]:
        """Apply one position-change event. The same event id is a no-op."""
        from app.domains.sys.models import (
            ChangeLog,
            Menu,
            Role,
            RoleMenu,
            RolePermDetail,
            UserRole,
        )

        session = get_db_session()
        tenant_id = ctx.tenant_id
        seen = session.query(ChangeLog).filter(
            ChangeLog.biz_type == "position_event",
            ChangeLog.biz_id == event_id,
            ChangeLog.deleted == 0,
        ).first()
        if seen is not None:
            return {"applied": False, "event_id": event_id}

        role = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.position_code == position_code,
            Role.deleted == 0,
        ).first()
        created = False
        if role is None:
            role = Role(
                tenant_id=tenant_id,
                role_key=f"auto_{position_code}",
                name=f"岗位{position_code}",
                source="DINGTALK_AUTO",
                status="PENDING_CONFIG",
                position_code=position_code,
            )
            assign_pk(session, role)
            session.add(role)
            session.flush()
            created = True
            self._notify_holders(session, tenant_id, event_id, position_code)

        current_links = session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
        ).all()
        roles_removed = False
        for link in current_links:
            if link.source != "DINGTALK_AUTO" or link.manual_removed:
                continue
            linked = session.query(Role).filter(Role.id == link.role_id).first()
            if linked is None or linked.position_code == position_code:
                continue
            session.delete(link)
            roles_removed = True
        session.flush()
        
        if roles_removed:
            from app.services.auth import AuthService
            AuthService.bump_user_perm_version(user_id)

        existing = session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
        ).first()
        role_changed = False
        if existing is None:
            link = UserRole(
                tenant_id=tenant_id,
                user_id=user_id,
                role_id=role.id,
                source="DINGTALK_AUTO",
                manual_removed=False,
            )
            assign_pk(session, link)
            session.add(link)
            role_changed = True
        elif existing.manual_removed:
            pass
        session.flush()
        
        if role_changed:
            from app.services.auth import AuthService
            AuthService.bump_user_perm_version(user_id)

        log = ChangeLog(
            tenant_id=tenant_id,
            biz_type="position_event",
            biz_id=event_id,
            field="position_code",
            after_value=position_code,
            reason="USER_EDIT",
        )
        assign_pk(session, log)
        session.add(log)
        session.flush()

        perm_count = session.query(RolePermDetail).filter(
            RolePermDetail.role_id == role.id,
            RolePermDetail.deleted == 0,
        ).count()
        menu_count = session.query(RoleMenu).filter(RoleMenu.role_id == role.id).count()
        menu_known = session.query(Menu).filter(Menu.deleted == 0).count()
        return {
            "applied": True,
            "created_role": created,
            "role_id": role.id,
            "perm_count": perm_count + (0 if menu_known >= 0 else 0),
            "menu_count": menu_count,
        }

    def update_rule(self, position_code: str, new_role_id: int) -> None:
        """Point a position at a new role and archive the previous version."""
        from app.domains.sys.models import ChangeLog, Role

        session = get_db_session()
        tenant_id = ctx.tenant_id
        old = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.position_code == position_code,
            Role.deleted == 0,
        ).first()
        new = session.query(Role).filter(
            Role.id == new_role_id,
            Role.tenant_id == tenant_id,
            Role.deleted == 0,
        ).first()
        if new is None:
            raise BizError(1504)
        before = str(old.id) if old is not None else ""
        if old is not None and old.id != new.id:
            old.position_code = None
            session.flush()
        new.position_code = position_code
        log = ChangeLog(
            tenant_id=tenant_id,
            biz_type="position_rule",
            biz_id=position_code,
            field="role_id",
            before_value=before,
            after_value=str(new.id),
            reason="USER_EDIT",
        )
        assign_pk(session, log)
        session.add(log)
        session.flush()

    def _notify_holders(
        self, session: Any, tenant_id: int, event_id: str, position_code: str
    ) -> None:
        from app.domains.sys.models import Menu, Role, RoleMenu, TodoItem, UserRole

        menu_ids = [
            row.id
            for row in session.query(Menu).filter(
                Menu.perm_code == HOLDER_PERM,
                Menu.deleted == 0,
            ).all()
        ]
        if not menu_ids:
            return
        role_ids = {
            row.role_id
            for row in session.query(RoleMenu).filter(RoleMenu.menu_id.in_(menu_ids)).all()
        }
        enabled = {
            row.id
            for row in session.query(Role).filter(
                Role.id.in_(role_ids or [-1]),
                Role.status == "ENABLED",
                Role.deleted == 0,
            ).all()
        }
        holders = {
            row.user_id
            for row in session.query(UserRole).filter(
                UserRole.role_id.in_(enabled or [-1]),
            ).all()
        }
        for user_id in holders:
            todo = TodoItem(
                tenant_id=tenant_id,
                assignee_user_id=user_id,
                title=f"请配置岗位{position_code}的自动角色",
                event_id=event_id,
                status="OPEN",
            )
            assign_pk(session, todo)
            session.add(todo)
        session.flush()
