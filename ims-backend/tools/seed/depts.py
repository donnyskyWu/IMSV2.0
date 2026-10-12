"""
Department seed data (FP-B08-01, FP-H05-01).

Per tenant initialization:
- Root department (source=LOCAL or DINGTALK if connected)
- System department "待分配" (source=SYSTEM)
"""

from datetime import datetime


def seed_depts(env: str, dry_run: bool = False) -> int:
    """
    Seed root and system departments.
    
    Rules per FP-B08-01:
    - Root department with parent_id=0
    - System department "待分配" under root, source=SYSTEM
    - Cannot be deleted, renamed, moved, or disabled
    
    Returns:
        Number of records upserted
    """
    if dry_run:
        print("  Would seed root department")
        print("  Would seed '待分配' system department")
        return 2
    
    from app.db.session import get_db_session
    from app.domains.sys.models import Dept
    
    session = get_db_session()
    now = datetime.now()
    count = 0
    
    # Seed for platform tenant (id=1)
    tenant_id = 1
    
    # Check if root department exists
    root = session.query(Dept).filter(
        Dept.tenant_id == tenant_id,
        Dept.parent_id == 0,
        Dept.deleted == 0,
    ).first()
    
    if not root:
        root = Dept(
            tenant_id=tenant_id,
            parent_id=0,
            path="/",
            name="公司",
            sort=0,
            status="ENABLED",
            source="LOCAL",
            creator=0,
            create_time=now,
        )
        session.add(root)
        session.flush()
        
        # Update path with id
        root.path = f"/{root.id}/"
        session.flush()
        count += 1
    
    # Check if system department exists
    system_dept = session.query(Dept).filter(
        Dept.tenant_id == tenant_id,
        Dept.source == "SYSTEM",
        Dept.deleted == 0,
    ).first()
    
    if not system_dept:
        system_dept = Dept(
            tenant_id=tenant_id,
            parent_id=root.id,
            path=f"{root.path}",  # Will be updated
            name="待分配",
            sort=999,
            status="ENABLED",
            source="SYSTEM",
            creator=0,
            create_time=now,
        )
        session.add(system_dept)
        session.flush()
        
        # Update path with id
        system_dept.path = f"{root.path}{system_dept.id}/"
        session.flush()
        count += 1
    
    session.commit()
    return count
