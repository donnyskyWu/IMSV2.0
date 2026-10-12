# app/services/migration_seed.py - OPS user seed framework (FP-H05-02)
"""Import sample OPS users twice with the same result. This is not a live OPS cutover."""

from typing import Any, Optional

from app.db.ids import assign_pk
from app.db.session import get_db_session

MIGRATION_USERNAME = "data-migration"


class MigrationSeedService:
    """Keep source primary keys and park orphan department references."""

    def __init__(self) -> None:
        self.report: dict[str, int] = {}

    def migration_user_id(self, session: Any) -> int:
        from app.domains.sys.models import User

        user = session.query(User).filter(User.username == MIGRATION_USERNAME).first()
        if user is None:
            user = User(
                id=1_000_000,
                tenant_id=1,
                username=MIGRATION_USERNAME,
                nickname="数据迁移",
                status="ACTIVE",
                source="MIGRATED",
            )
            session.add(user)
            session.flush()
        return user.id

    def import_users(
        self,
        rows: list[dict[str, Any]],
        valid_dept_ids: set[int],
    ) -> dict[str, int]:
        from app.core.clock import get_now
        from app.domains.sys.models import IntegrityScan, MigrationPending, User

        session = get_db_session()
        creator = self.migration_user_id(session)
        success = 0
        pending = 0
        for row in rows:
            if row["dept_id"] not in valid_dept_ids:
                exists = session.query(MigrationPending).filter(
                    MigrationPending.source_id == row["id"],
                    MigrationPending.deleted == 0,
                ).first()
                if exists is None:
                    item = MigrationPending(
                        tenant_id=1,
                        source_id=row["id"],
                        reason="部门不存在",
                        creator=creator,
                    )
                    assign_pk(session, item)
                    session.add(item)
                pending += 1
                continue
            user = session.query(User).filter(User.id == row["id"]).first()
            if user is None:
                user = User(
                    id=row["id"],
                    tenant_id=1,
                    username=row["username"],
                    nickname=row["nickname"],
                    status="ACTIVE",
                    source="MIGRATED",
                    main_dept_id=row["dept_id"],
                    creator=creator,
                )
                session.add(user)
            success += 1
        scan = session.query(IntegrityScan).filter(
            IntegrityScan.tables_scanned == "migration",
        ).first()
        if scan is None:
            scan = IntegrityScan(
                tenant_id=1,
                start_time=get_now(),
                tables_scanned="migration",
                issue_count=pending,
                status="SUCCESS",
                creator=creator,
            )
            assign_pk(session, scan)
            session.add(scan)
        session.flush()
        self.report = {"source": len(rows), "success": success, "pending": pending}
        return self.report

    def next_user_id(self) -> int:
        from app.domains.sys.models import User

        session = get_db_session()
        last = session.query(User.id).order_by(User.id.desc()).limit(1).scalar()
        return int(last or 0) + 1


def build_sample(valid_dept: int, count: int = 100) -> list[dict[str, Any]]:
    rows = []
    for index in range(1, count + 1):
        dept_id: Optional[int] = valid_dept if index < count else 999999
        rows.append({
            "id": index,
            "username": f"ops_{index:03d}",
            "nickname": f"用户{index}",
            "dept_id": dept_id,
        })
    return rows
