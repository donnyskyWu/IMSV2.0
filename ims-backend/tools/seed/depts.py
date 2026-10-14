"""
Department seed data (FP-B08-01, FP-H05-01).

Per tenant initialization:
- Root department (source=LOCAL or DINGTALK if connected)
- System department "待分配" (source=SYSTEM)
"""

from tools.seed.timeutil import seed_now

# 02 §0.2 账号所在部门。只在 e2e 环境补，挂在根部门下。
E2E_DEPT_NAMES = ["信息部", "行政部", "运营中心", "市场一部", "市场二部"]


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
        extra = len(E2E_DEPT_NAMES) + 1 if env == "e2e" else 0
        return 2 + extra

    from app.db.session import get_db_session
    from app.domains.sys.models import Dept

    session = get_db_session()
    now = seed_now()
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

    if env == "e2e":
        count += _seed_e2e_depts(session, Dept, root, now)

    session.commit()
    return count


def _seed_e2e_depts(session, dept_cls, root, now) -> int:
    """补 02 账号用的部门。同名已存在则跳过，不改名。"""
    count = 0
    for index, name in enumerate(E2E_DEPT_NAMES, start=1):
        count += _ensure_child(session, dept_cls, root, name, index, now)
    # 租户 2 根部门，给 test_t2 用。已存在则不改。
    second_root = session.query(dept_cls).filter(
        dept_cls.tenant_id == 2,
        dept_cls.parent_id == 0,
        dept_cls.deleted == 0,
    ).first()
    if second_root is None:
        second_root = dept_cls(
            tenant_id=2,
            parent_id=0,
            path="/",
            name="公司",
            sort=0,
            status="ENABLED",
            source="LOCAL",
            creator=0,
            create_time=now,
        )
        session.add(second_root)
        session.flush()
        second_root.path = f"/{second_root.id}/"
        session.flush()
        count += 1
    return count


def _ensure_child(session, dept_cls, root, name: str, sort: int, now) -> int:
    found = session.query(dept_cls).filter(
        dept_cls.tenant_id == root.tenant_id,
        dept_cls.name == name,
        dept_cls.deleted == 0,
    ).first()
    if found is not None:
        return 0
    child = dept_cls(
        tenant_id=root.tenant_id,
        parent_id=root.id,
        path=root.path,
        name=name,
        sort=sort,
        status="ENABLED",
        source="LOCAL",
        creator=0,
        create_time=now,
    )
    session.add(child)
    session.flush()
    child.path = f"{root.path}{child.id}/"
    session.flush()
    return 1
