"""
System parameter seed data (FP-B07-02, FP-H05-01).

First batch parameters per FP-B07-02:
- work.task.confirm.auto-ai-generate
- content.review.level1.role / level2.role (ROLE_REF)
- dingtalk.notify.enabled
- dingtalk.sync.enabled
- air.key.ip_whitelist.enabled
- perf.grade.excellent / qualified
- dingtalk_attendance.* (FP-H07-01)

Note: Train AI config is NOT in system params (goes to B10 AI Resource Center).
"""

from tools.seed.timeutil import seed_now

PARAMS = [
    # 通用
    {
        "param_key": "work.task.confirm.auto-ai-generate",
        "name": "工作任务确认时自动AI生成",
        "group": "通用",
        "value_type": "BOOLEAN",
        "default_value": "false",
        "value": "false",
    },

    # 内容审核
    {
        "param_key": "content.review.level1.role",
        "name": "一级审核角色",
        "group": "内容审核",
        "value_type": "ROLE_REF",
        "default_value": "",
        "value": "",
        "remark": "存角色ID",
    },
    {
        "param_key": "content.review.level2.role",
        "name": "二级审核角色",
        "group": "内容审核",
        "value_type": "ROLE_REF",
        "default_value": "",
        "value": "",
        "remark": "存角色ID",
    },

    # 钉钉
    {
        "param_key": "dingtalk.notify.enabled",
        "name": "钉钉通知开关",
        "group": "钉钉",
        "value_type": "BOOLEAN",
        "default_value": "true",
        "value": "true",
    },
    {
        "param_key": "dingtalk.sync.enabled",
        "name": "钉钉组织同步开关",
        "group": "钉钉",
        "value_type": "BOOLEAN",
        "default_value": "true",
        "value": "true",
    },

    # AI
    {
        "param_key": "air.key.ip_whitelist.enabled",
        "name": "IP白名单功能开关",
        "group": "AI",
        "value_type": "BOOLEAN",
        "default_value": "false",
        "value": "false",
    },

    # 绩效 (【裁定】C011)
    {
        "param_key": "perf.grade.excellent",
        "name": "绩效优秀分数线",
        "group": "通用",
        "value_type": "NUMBER",
        "default_value": "85",
        "value": "85",
        "min_value": "0",
        "max_value": "100",
    },
    {
        "param_key": "perf.grade.qualified",
        "name": "绩效合格分数线",
        "group": "通用",
        "value_type": "NUMBER",
        "default_value": "60",
        "value": "60",
        "min_value": "0",
        "max_value": "100",
    },

    # 钉钉考勤 (FP-H07-01)
    {
        "param_key": "dingtalk_attendance.enabled",
        "name": "钉钉考勤功能开关",
        "group": "钉钉考勤",
        "value_type": "BOOLEAN",
        "default_value": "false",
        "value": "false",
    },
    {
        "param_key": "dingtalk_attendance.mode",
        "name": "钉钉考勤模式",
        "group": "钉钉考勤",
        "value_type": "ENUM",
        "default_value": "mock",
        "value": "mock",
        "options": '["real", "mock"]',
    },
    {
        "param_key": "dingtalk_attendance.app_key",
        "name": "钉钉考勤AppKey",
        "group": "钉钉考勤",
        "value_type": "TEXT",
        "default_value": "",
        "value": "",
    },
    {
        "param_key": "dingtalk_attendance.app_secret",
        "name": "钉钉考勤AppSecret",
        "group": "钉钉考勤",
        "value_type": "SECRET",
        "default_value": "",
        "value": "",
        "remark": "加密存储，显示脱敏",
    },
    {
        "param_key": "dingtalk_attendance.base_url",
        "name": "钉钉考勤API地址",
        "group": "钉钉考勤",
        "value_type": "TEXT",
        "default_value": "https://oapi.dingtalk.com",
        "value": "https://oapi.dingtalk.com",
    },
    {
        "param_key": "dingtalk_attendance.timeout_ms",
        "name": "钉钉考勤超时时间(毫秒)",
        "group": "钉钉考勤",
        "value_type": "NUMBER",
        "default_value": "5000",
        "value": "5000",
        "min_value": "1000",
        "max_value": "30000",
    },
]


def seed_params(env: str, dry_run: bool = False) -> int:
    """
    Seed system parameters.

    Rules per FP-H05-01:
    - Upsert by param_key
    - Does not overwrite admin-modified values

    Returns:
        Number of records upserted
    """
    if dry_run:
        print(f"  Would seed {len(PARAMS)} parameters")
        return len(PARAMS)

    from app.db.session import get_db_session
    from app.domains.sys.models import SysParam

    session = get_db_session()
    count = 0
    now = seed_now()

    for p in PARAMS:
        existing = session.query(SysParam).filter(
            SysParam.param_key == p["param_key"],
            SysParam.deleted == 0,
        ).first()

        if not existing:
            obj = SysParam(
                tenant_id=1,
                param_key=p["param_key"],
                name=p["name"],
                group=p["group"],
                value_type=p["value_type"],
                value=p.get("value"),
                default_value=p.get("default_value"),
                min_value=p.get("min_value"),
                max_value=p.get("max_value"),
                options=p.get("options"),
                is_builtin=True,
                remark=p.get("remark"),
                creator=0,
                create_time=now,
            )
            session.add(obj)
            count += 1

    session.commit()
    return count
