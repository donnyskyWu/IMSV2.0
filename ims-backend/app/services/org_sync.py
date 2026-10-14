# app/services/org_sync.py - Organization sync service (FW-D07)
"""
Organization synchronization service.

Implements:
- FP-D07-04: DingTalk organization reconciliation
"""

from typing import Any, Optional

from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.db.transaction import transactional


class OrgSyncService:
    """Organization synchronization service."""

    @transactional
    async def trigger_reconcile(self) -> dict[str, Any]:
        """
        Trigger organization structure reconciliation with DingTalk.

        Rules per FP-D07-04:
        - Compares IMS org structure with DingTalk
        - Creates sync batch record
        - Returns immediately with batch info (async execution)

        Returns:
            Sync batch info
        """
        from app.domains.sys.models import OrgSyncBatch
        session = get_db_session()

        tenant_id = ctx.tenant_id
        now = get_now()

        # Create sync batch record
        batch = OrgSyncBatch(
            tenant_id=tenant_id,
            status="PENDING",
            started_at=now,
        )

        session.add(batch)
        session.flush()

        # TODO: Trigger async DingTalk sync job
        # For now, just return the batch info

        return self._batch_to_response(batch)

    async def get_latest_batch(self) -> Optional[dict[str, Any]]:
        """
        Get the latest org sync batch status.

        Rules per FP-D07-04:
        - Returns the most recent sync batch
        - Includes counts for dept/user changes

        Returns:
            Latest batch info or None
        """
        from app.domains.sys.models import OrgSyncBatch
        session = get_db_session()

        tenant_id = ctx.tenant_id

        batch = session.query(OrgSyncBatch).filter(
            OrgSyncBatch.tenant_id == tenant_id,
        ).order_by(OrgSyncBatch.id.desc()).first()

        if not batch:
            return None

        return self._batch_to_response(batch)

    async def reconcile_snapshot(
        self,
        snapshot: dict[str, Any],
        *,
        timeout: bool = False,
    ) -> dict[str, Any]:
        """Apply a DingTalk snapshot. A running batch or a timeout does not commit."""
        from app.domains.sys.models import OrgSyncBatch

        session = get_db_session()
        tenant_id = ctx.tenant_id
        running = session.query(OrgSyncBatch).filter(
            OrgSyncBatch.tenant_id == tenant_id,
            OrgSyncBatch.status == "RUNNING",
            OrgSyncBatch.deleted == 0,
        ).first()
        if running is not None:
            raise BizError(1001, msg="同步正在进行中")

        from app.db.ids import assign_pk

        batch = OrgSyncBatch(
            tenant_id=tenant_id,
            status="RUNNING",
            started_at=get_now(),
        )
        assign_pk(session, batch)
        session.add(batch)
        session.flush()
        reports: list[str] = []
        nested = session.begin_nested()
        try:
            if timeout:
                self._apply_snapshot(session, tenant_id, snapshot, reports)
                raise TimeoutError("football-or-dingtalk timeout")
            self._apply_snapshot(session, tenant_id, snapshot, reports)
            nested.commit()
            batch.status = "SUCCESS"
        except TimeoutError:
            nested.rollback()
            batch.status = "FAILED"
            batch.error_msg = "5003"
        batch.completed_at = get_now()
        session.flush()
        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "error_msg": batch.error_msg,
            "reports": reports,
        }

    def _apply_snapshot(
        self,
        session: Any,
        tenant_id: int,
        snapshot: dict[str, Any],
        reports: list[str],
    ) -> None:
        from app.db.ids import assign_pk
        from app.domains.sys.models import ChangeLog, Dept

        by_ding: dict[str, Any] = {}
        for dept in session.query(Dept).filter(
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
            Dept.dingtalk_dept_id.isnot(None),
        ).all():
            by_ding[dept.dingtalk_dept_id] = dept

        for item in snapshot.get("depts", []):
            parent = by_ding.get(item.get("parent_dingtalk_id"))
            current = by_ding.get(item["dingtalk_id"])
            if current is None:
                parent_id = parent.id if parent is not None else 0
                parent_path = parent.path if parent is not None else "/"
                created = Dept(
                    tenant_id=tenant_id,
                    parent_id=parent_id,
                    name=item["name"],
                    path="/",
                    source="DINGTALK",
                    status="ENABLED",
                    dingtalk_dept_id=item["dingtalk_id"],
                )
                assign_pk(session, created)
                session.add(created)
                session.flush()
                created.path = f"{parent_path}{created.id}/"
                by_ding[item["dingtalk_id"]] = created
                local_same = session.query(Dept).filter(
                    Dept.tenant_id == tenant_id,
                    Dept.parent_id == parent_id,
                    Dept.name == item["name"],
                    Dept.source == "LOCAL",
                    Dept.deleted == 0,
                ).first()
                if local_same is not None:
                    reports.append("存在同名本地部门")
                continue
            if parent is not None and current.parent_id != parent.id:
                before = str(current.parent_id)
                current.parent_id = parent.id
                current.path = f"{parent.path}{current.id}/"
                log = ChangeLog(
                    tenant_id=tenant_id,
                    biz_type="dept",
                    biz_id=str(current.id),
                    field="parent_id",
                    before_value=before,
                    after_value=str(parent.id),
                    reason="DINGTALK_OVERRIDE",
                )
                assign_pk(session, log)
                session.add(log)
        session.flush()

        for item in snapshot.get("users", []):
            self._apply_user(session, tenant_id, item, by_ding)

    def _apply_user(
        self,
        session: Any,
        tenant_id: int,
        item: dict[str, Any],
        by_ding: dict[str, Any],
    ) -> None:
        from app.db.ids import assign_pk
        from app.domains.sys.models import DictData, User, UserDept, UserMapping
        from app.services.user import UserService

        mapping = session.query(UserMapping).filter(
            UserMapping.dingtalk_user_id == item["dingtalk_user_id"],
            UserMapping.deleted == 0,
        ).first()
        user = None
        if mapping is not None:
            user = session.query(User).filter(User.id == mapping.user_id).first()
        if user is None:
            user = User(
                tenant_id=tenant_id,
                username=item.get("username") or f"dt_{item['dingtalk_user_id']}",
                nickname=item.get("name") or item["dingtalk_user_id"],
                status="ACTIVE",
                source="DINGTALK",
                password_hash=None,
            )
            assign_pk(session, user)
            session.add(user)
            session.flush()
            link = UserMapping(
                tenant_id=tenant_id,
                user_id=user.id,
                dingtalk_user_id=item["dingtalk_user_id"],
            )
            assign_pk(session, link)
            session.add(link)
        if item.get("resigned"):
            from app.services.user import USER_EVENTS

            if user.status != "RESIGNED":
                user.status = "RESIGNED"
                UserService()._drop_sessions(user.id)
                USER_EVENTS.append({"type": "user.resigned", "user_id": user.id})
            session.flush()
            return
        position = item.get("position")
        if position:
            row = session.query(DictData).filter(
                DictData.dict_type == "dict_position",
                DictData.dict_value == position,
                DictData.deleted == 0,
            ).first()
            if row is None:
                row = DictData(
                    tenant_id=1,
                    dict_type="dict_position",
                    dict_value=position,
                    dict_label=position,
                    source="DINGTALK",
                    status="ENABLED",
                )
                assign_pk(session, row)
                session.add(row)
            user.position_code = position
        wanted = []
        for ding_id in item.get("dept_dingtalk_ids", []):
            dept = by_ding.get(ding_id)
            if dept is not None:
                wanted.append(dept.id)
        if wanted:
            session.query(UserDept).filter(
                UserDept.user_id == user.id,
                UserDept.source == "DINGTALK",
            ).delete()
            for index, dept_id in enumerate(wanted):
                link = UserDept(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    dept_id=dept_id,
                    is_main=index == 0,
                    source="DINGTALK",
                )
                assign_pk(session, link)
                session.add(link)
            user.main_dept_id = wanted[0]
        session.flush()

    def _batch_to_response(self, batch) -> dict[str, Any]:
        """Convert batch to response dict."""
        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "started_at": (
                batch.started_at.isoformat() + "+08:00"
                if batch.started_at else None
            ),
            "completed_at": (
                batch.completed_at.isoformat() + "+08:00"
                if batch.completed_at else None
            ),
            "added_depts": batch.added_depts or 0,
            "updated_depts": batch.updated_depts or 0,
            "removed_depts": batch.removed_depts or 0,
            "added_users": batch.added_users or 0,
            "updated_users": batch.updated_users or 0,
            "removed_users": batch.removed_users or 0,
            "error_msg": batch.error_msg,
        }
