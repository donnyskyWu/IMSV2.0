"""
Tenant seed data (FP-B04-04, FP-H05-01).

Platform tenant (id=1) has all menus, not limited by package.
"""

from tools.seed.timeutil import seed_now


def seed_tenant(env: str, dry_run: bool = False) -> int:
    """
    Seed platform tenant.
    
    Rules per FP-B04-04:
    - tenant_id=1 is platform tenant
    - Has all menus, not limited by package
    
    Returns:
        Number of records upserted
    """
    if dry_run:
        extra = 1 if env == "e2e" else 0
        print("  Would seed platform tenant (id=1)")
        return 1 + extra

    from app.db.session import get_db_session
    from app.domains.sys.models import Tenant

    session = get_db_session()
    now = seed_now()
    count = 0

    # 平台租户已存在则不改名称和状态。
    existing = session.query(Tenant).filter(Tenant.id == 1).first()
    if not existing:
        session.add(Tenant(
            id=1,
            tenant_id=1,
            name="平台租户",
            status="ENABLED",
            creator=0,
            create_time=now,
        ))
        count += 1

    # 02 §0.2 test_t2 所属租户。已存在则不改状态，避免覆盖管理员重新启用。
    if env == "e2e":
        second = session.query(Tenant).filter(Tenant.id == 2).first()
        if second is None:
            session.add(Tenant(
                id=2,
                tenant_id=2,
                name="测试停用租户",
                status="DISABLED",
                creator=0,
                create_time=now,
            ))
            count += 1

    session.commit()
    return count
