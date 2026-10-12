"""
Tenant seed data (FP-B04-04, FP-H05-01).

Platform tenant (id=1) has all menus, not limited by package.
"""

from datetime import datetime


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
        print("  Would seed platform tenant (id=1)")
        return 1
    
    from app.db.session import get_db_session
    from app.domains.sys.models import Tenant
    
    session = get_db_session()
    now = datetime.now()
    
    # Check if platform tenant exists
    existing = session.query(Tenant).filter(Tenant.id == 1).first()
    
    if not existing:
        tenant = Tenant(
            id=1,
            tenant_id=1,
            name="平台租户",
            status="ENABLED",
            creator=0,
            create_time=now,
        )
        session.add(tenant)
        session.commit()
        return 1
    
    return 0
