"""
Role seed data (FP-B04-01, FP-H05-01).

Standard roles R1-R11 with data scope.
Business code must NOT use role_key for permission checks.

Q10：R2 data_scope=DEPT（本部门、不含下级）。R4 data_scope=IP_GROUP。
角色名保持种子原值，不改成 01 里的「行政 / 运营总监」。
菜单授权在 grants.py，不在这里覆盖已有角色字段。
"""

from tools.seed.timeutil import seed_now

# Standard roles R1-R11
# 数据范围以本表为准。已存在的角色不更新 name / data_scope / sort / remark。
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
        "data_scope": "DEPT",  # Q10：本部门，不含下级
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
        "data_scope": "IP_GROUP",  # Q10：不是 ALL
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
            {
                "role_key": "e2e_live_ops",
                "name": "测试-直播运营",
                "data_scope": None,
                "remark": "E2E：02 未指定数据范围，保持未配置",
                "sort": 101,
            },
            {
                "role_key": "e2e_dept_view",
                "name": "测试-本部门查看",
                "data_scope": "DEPT",
                "remark": "E2E：本部门，不含下级",
                "sort": 102,
            },
        ]
        roles.extend(e2e_roles)

    if dry_run:
        # 停用租户另有一条 R1，不在上面的平台租户列表里。
        extra = 1 if env == "e2e" else 0
        print(f"  Would seed {len(roles) + extra} roles")
        return len(roles) + extra

    from app.db.session import get_db_session
    from app.domains.sys.models import Role

    session = get_db_session()
    now = seed_now()
    count = 0

    # 标准角色与 e2e_ 角色挂在平台租户。停用租户的 R1 在下面按租户补一行。
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

    if env == "e2e":
        count += _ensure_tenant_role(
            session,
            tenant_id=2,
            role_key="R1",
            name="超级管理员",
            data_scope="ALL",
            now=now,
        )

    session.commit()
    return count


def _ensure_tenant_role(session, tenant_id: int, role_key: str, name: str, data_scope: str, now) -> int:
    """停用租户需要自己的 R1。已存在则不改字段。"""
    from app.domains.sys.models import Role

    existing = session.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.role_key == role_key,
        Role.deleted == 0,
    ).first()
    if existing is not None:
        return 0
    session.add(Role(
        tenant_id=tenant_id,
        role_key=role_key,
        name=name,
        source="MANUAL",
        status="ENABLED",
        data_scope=data_scope,
        is_standard=True,
        sort=1,
        remark="E2E 停用租户的管理员角色",
        creator=0,
        create_time=now,
    ))
    return 1
