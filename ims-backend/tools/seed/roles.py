"""
Role seed data (FP-B04-01, FP-H05-01).

Standard roles R1-R11 with permissions, menus, data scope.
Business code must NOT use role_key for permission checks.
"""

from datetime import datetime

# Standard roles R1-R11
# Per spec, these are placeholders - actual permissions defined by M01/M02
STANDARD_ROLES = [
    {
        "role_key": "R1",
        "name": "超级管理员",
        "data_scope": "ALL",
        "remark": "拥有全部权限",
        "sort": 1,
    },
    {
        "role_key": "R2",
        "name": "部门管理员",
        "data_scope": "DEPT",
        "remark": "管理本部门数据",
        "sort": 2,
    },
    {
        "role_key": "R3",
        "name": "内容审核员",
        "data_scope": "ALL",
        "remark": "内容审核权限",
        "sort": 3,
    },
    {
        "role_key": "R4",
        "name": "IP组长",
        "data_scope": "IP_GROUP",
        "remark": "管理本IP组数据",
        "sort": 4,
    },
    {
        "role_key": "R5",
        "name": "运营人员",
        "data_scope": "SELF",
        "remark": "普通运营人员",
        "sort": 5,
    },
    {
        "role_key": "R6",
        "name": "财务人员",
        "data_scope": "ALL",
        "remark": "财务数据查看",
        "sort": 6,
    },
    {
        "role_key": "R7",
        "name": "数据分析员",
        "data_scope": "ALL",
        "remark": "数据分析查看",
        "sort": 7,
    },
    {
        "role_key": "R8",
        "name": "培训管理员",
        "data_scope": "ALL",
        "remark": "培训管理权限",
        "sort": 8,
    },
    {
        "role_key": "R9",
        "name": "只读财务",
        "data_scope": "ALL",
        "remark": "财务数据只读，成本脱敏",
        "sort": 9,
    },
    {
        "role_key": "R10",
        "name": "外部协作",
        "data_scope": "SELF",
        "remark": "外部协作人员",
        "sort": 10,
    },
    {
        "role_key": "R11",
        "name": "访客",
        "data_scope": None,
        "remark": "仅查看公开数据",
        "sort": 11,
    },
]


def seed_roles(env: str, dry_run: bool = False) -> int:
    """
    Seed standard roles R1-R11.
    
    Rules per FP-H05-01:
    - Upsert by role_key
    - Mark as is_standard=True
    - E2E roles use "测试-" prefix with e2e_ key prefix
    
    Returns:
        Number of records upserted
    """
    roles = STANDARD_ROLES.copy()

    # Add E2E roles if in e2e environment
    if env == "e2e":
        e2e_roles = [
            {
                "role_key": "e2e_tester",
                "name": "测试-测试人员",
                "data_scope": "ALL",
                "remark": "E2E测试角色",
                "sort": 100,
            },
        ]
        roles.extend(e2e_roles)

    if dry_run:
        print(f"  Would seed {len(roles)} roles")
        return len(roles)

    from app.db.session import get_db_session
    from app.domains.sys.models import Role

    session = get_db_session()
    now = datetime.now()
    count = 0

    # Seed for platform tenant (id=1)
    tenant_id = 1

    for r in roles:
        existing = session.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.role_key == r["role_key"],
            Role.deleted == 0,
        ).first()

        if not existing:
            is_standard = r["role_key"].startswith("R") and r["role_key"][1:].isdigit()

            role = Role(
                tenant_id=tenant_id,
                role_key=r["role_key"],
                name=r["name"],
                source="MANUAL",
                status="ENABLED",
                data_scope=r.get("data_scope"),
                is_standard=is_standard,
                sort=r.get("sort", 0),
                remark=r.get("remark"),
                creator=0,
                create_time=now,
            )
            session.add(role)
            count += 1

    session.commit()
    return count
