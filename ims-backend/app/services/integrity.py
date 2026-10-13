# app/services/integrity.py - Reference integrity scan (FP-B09)
"""Read-only scan that records four issue types and notifies holders."""

from typing import Any, Optional

from app.core.clock import get_now
from app.core.context import ctx
from app.db.ids import assign_pk
from app.db.session import get_db_session

INTEGRITY_PERM = "ims:system:integrity:query"


class IntegrityService:
    """Scan ``ims_ref_probe`` without modifying the probed rows."""

    def __init__(self) -> None:
        self.last_filter = ""

    def scan(self, tenant_id: Optional[int] = None) -> dict[str, Any]:
        from app.domains.sys.models import Dept, IntegrityIssue, IntegrityScan, RefProbe

        session = get_db_session()
        tid = ctx.tenant_id if tenant_id is None else tenant_id
        self.last_filter = f"tenant_id={tid}"
        now = get_now()
        batch = IntegrityScan(
            tenant_id=tid,
            start_time=now,
            tables_scanned="ims_ref_probe",
            issue_count=0,
            status="RUNNING",
        )
        assign_pk(session, batch)
        session.add(batch)
        session.flush()

        probes = session.query(RefProbe).filter(
            RefProbe.tenant_id == tid,
            RefProbe.deleted == 0,
        ).all()
        found: list[dict[str, str]] = []
        for probe in probes:
            if probe.dept_id is None and probe.external_room_id:
                continue
            if probe.dept_id is not None:
                dept = session.query(Dept).filter(Dept.id == probe.dept_id).first()
                if dept is None or dept.deleted:
                    found.append(self._issue(
                        "ORPHAN", probe, "dept_id", "ims_sys_dept", str(probe.dept_id),
                    ))
                elif dept.tenant_id != probe.tenant_id:
                    found.append(self._issue(
                        "CROSS_TENANT", probe, "dept_id", "ims_sys_dept", str(dept.id),
                    ))
                elif dept.status != "ENABLED":
                    found.append(self._issue(
                        "DISABLED_REF", probe, "dept_id", "ims_sys_dept", str(dept.id),
                    ))
            if probe.parent_probe_id:
                parent = session.query(RefProbe).filter(
                    RefProbe.id == probe.parent_probe_id,
                ).first()
                if parent is not None and parent.deleted and probe.deleted == 0:
                    found.append(self._issue(
                        "CASCADE_MISSED", probe, "parent_probe_id",
                        "ims_ref_probe", str(parent.id),
                    ))

        for item in found:
            existing = session.query(IntegrityIssue).filter(
                IntegrityIssue.tenant_id == tid,
                IntegrityIssue.issue_type == item["issue_type"],
                IntegrityIssue.record_id == item["record_id"],
                IntegrityIssue.field == item["field"],
                IntegrityIssue.deleted == 0,
            ).first()
            if existing is None:
                row = IntegrityIssue(
                    tenant_id=tid,
                    scan_id=batch.id,
                    issue_type=item["issue_type"],
                    table_name="ims_ref_probe",
                    record_id=item["record_id"],
                    field=item["field"],
                    target_table=item["target_table"],
                    target_id=item["target_id"],
                    status="OPEN",
                    last_seen_time=now,
                )
                assign_pk(session, row)
                session.add(row)
            else:
                existing.last_seen_time = now
                existing.scan_id = batch.id

        if found:
            self._notify(session, tid, len(found))

        batch.issue_count = len(found)
        batch.status = "SUCCESS"
        batch.end_time = now
        session.flush()
        types = sorted({item["issue_type"] for item in found})
        return {"count": len(found), "types": types, "filter": self.last_filter}

    def _issue(
        self, kind: str, probe: Any, field: str, target: str, target_id: str,
    ) -> dict[str, str]:
        return {
            "issue_type": kind,
            "record_id": str(probe.id),
            "field": field,
            "target_table": target,
            "target_id": target_id,
        }

    def _notify(self, session: Any, tenant_id: int, count: int) -> None:
        from app.domains.sys.models import Menu, Role, RoleMenu, UserRole
        from app.services import message as message_service

        menus = [
            row.id
            for row in session.query(Menu).filter(
                Menu.perm_code == INTEGRITY_PERM,
                Menu.deleted == 0,
            ).all()
        ]
        if not menus:
            return
        role_ids = {
            row.role_id
            for row in session.query(RoleMenu).filter(RoleMenu.menu_id.in_(menus)).all()
        }
        enabled = {
            row.id
            for row in session.query(Role).filter(
                Role.id.in_(role_ids or [-1]),
                Role.status == "ENABLED",
                Role.deleted == 0,
            ).all()
        }
        holders = list({
            row.user_id
            for row in session.query(UserRole).filter(
                UserRole.role_id.in_(enabled or [-1]),
            ).all()
        })
        if holders:
            message_service.notify(
                session,
                event_type="integrity_scan",
                biz_key=f"integrity_scan_{tenant_id}",
                receivers=holders,
                title="数据完整性巡检",
                content=f"发现 {count} 条问题",
                source_module="数据完整性",
                route="/ims/system/integrity",
            )
