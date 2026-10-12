"""
Dictionary seed data (FP-B07-02, FP-H05-01).

First batch dictionaries:
- dict_user_status: ACTIVE/FROZEN/RESIGNED
- dict_dept_source: DINGTALK/LOCAL/SYSTEM
- dict_role_source: MANUAL/DINGTALK_AUTO
- dict_role_status: ENABLED/DISABLED/PENDING_CONFIG
- dict_data_scope: ALL/DEPT/IP_GROUP/SELF
- dict_position: (岗位，由钉钉同步补充)
- dict_platform_type: DOUYIN/KUAISHOU/WECHAT_CHANNELS/XIAOHONGSHU/WECHAT_MP/OTHER
- dict_common_status: ENABLED/DISABLED
- dict_org_sync_status: PENDING/RUNNING/SUCCESS/FAILED
- dict_todo_status, dict_msg_type, etc.
"""

from datetime import datetime

DICT_TYPES = [
    {"dict_type": "dict_user_status", "name": "用户状态"},
    {"dict_type": "dict_dept_source", "name": "部门来源"},
    {"dict_type": "dict_role_source", "name": "角色来源"},
    {"dict_type": "dict_role_status", "name": "角色状态"},
    {"dict_type": "dict_data_scope", "name": "数据范围"},
    {"dict_type": "dict_position", "name": "岗位"},
    {"dict_type": "dict_platform_type", "name": "平台类型"},
    {"dict_type": "dict_common_status", "name": "通用状态"},
    {"dict_type": "dict_org_sync_status", "name": "组织同步状态"},
    {"dict_type": "dict_todo_type", "name": "待办类型"},
    {"dict_type": "dict_todo_status", "name": "待办状态"},
    {"dict_type": "dict_msg_type", "name": "消息类型"},
    {"dict_type": "dict_sop_node_type", "name": "SOP节点类型"},
    {"dict_type": "dict_document_type", "name": "文档类型"},
    {"dict_type": "dict_marketing_plan_type", "name": "营销计划类型"},
    {"dict_type": "dict_content_type", "name": "内容类型"},
]

DICT_DATA = [
    # dict_user_status
    {"dict_type": "dict_user_status", "dict_value": "ACTIVE", "dict_label": "在职", "color_type": "success", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_user_status", "dict_value": "FROZEN", "dict_label": "冻结", "color_type": "warning", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_user_status", "dict_value": "RESIGNED", "dict_label": "离职", "color_type": "neutral", "sort": 3, "is_builtin": True},

    # dict_dept_source
    {"dict_type": "dict_dept_source", "dict_value": "DINGTALK", "dict_label": "钉钉同步", "color_type": "primary", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_dept_source", "dict_value": "LOCAL", "dict_label": "本地", "color_type": "info", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_dept_source", "dict_value": "SYSTEM", "dict_label": "系统", "color_type": "neutral", "sort": 3, "is_builtin": True},

    # dict_role_source
    {"dict_type": "dict_role_source", "dict_value": "MANUAL", "dict_label": "手工", "color_type": "primary", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_role_source", "dict_value": "DINGTALK_AUTO", "dict_label": "钉钉自动", "color_type": "info", "sort": 2, "is_builtin": True},

    # dict_role_status
    {"dict_type": "dict_role_status", "dict_value": "ENABLED", "dict_label": "启用", "color_type": "success", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_role_status", "dict_value": "DISABLED", "dict_label": "停用", "color_type": "neutral", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_role_status", "dict_value": "PENDING_CONFIG", "dict_label": "待配置", "color_type": "warning", "sort": 3, "is_builtin": True},

    # dict_data_scope
    {"dict_type": "dict_data_scope", "dict_value": "ALL", "dict_label": "全部数据", "color_type": "primary", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_data_scope", "dict_value": "DEPT", "dict_label": "本部门", "color_type": "info", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_data_scope", "dict_value": "IP_GROUP", "dict_label": "本IP组", "color_type": "purple", "sort": 3, "is_builtin": True},
    {"dict_type": "dict_data_scope", "dict_value": "SELF", "dict_label": "仅本人", "color_type": "neutral", "sort": 4, "is_builtin": True},

    # dict_platform_type (FP-C04-02)
    {"dict_type": "dict_platform_type", "dict_value": "DOUYIN", "dict_label": "抖音", "color_type": "danger", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_platform_type", "dict_value": "KUAISHOU", "dict_label": "快手", "color_type": "warning", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_platform_type", "dict_value": "WECHAT_CHANNELS", "dict_label": "视频号", "color_type": "success", "sort": 3, "is_builtin": True},
    {"dict_type": "dict_platform_type", "dict_value": "XIAOHONGSHU", "dict_label": "小红书", "color_type": "danger", "sort": 4, "is_builtin": True},
    {"dict_type": "dict_platform_type", "dict_value": "WECHAT_MP", "dict_label": "公众号", "color_type": "success", "sort": 5, "is_builtin": True},
    {"dict_type": "dict_platform_type", "dict_value": "OTHER", "dict_label": "其他", "color_type": "neutral", "sort": 99, "is_builtin": True},

    # dict_common_status
    {"dict_type": "dict_common_status", "dict_value": "ENABLED", "dict_label": "启用", "color_type": "success", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_common_status", "dict_value": "DISABLED", "dict_label": "停用", "color_type": "neutral", "sort": 2, "is_builtin": True},

    # dict_org_sync_status
    {"dict_type": "dict_org_sync_status", "dict_value": "PENDING", "dict_label": "待执行", "color_type": "neutral", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_org_sync_status", "dict_value": "RUNNING", "dict_label": "执行中", "color_type": "primary", "sort": 2, "is_builtin": True},
    {"dict_type": "dict_org_sync_status", "dict_value": "SUCCESS", "dict_label": "成功", "color_type": "success", "sort": 3, "is_builtin": True},
    {"dict_type": "dict_org_sync_status", "dict_value": "FAILED", "dict_label": "失败", "color_type": "danger", "sort": 4, "is_builtin": True},

    # dict_todo_status (placeholder)
    {"dict_type": "dict_todo_status", "dict_value": "PENDING", "dict_label": "待处理", "color_type": "warning", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_todo_status", "dict_value": "DONE", "dict_label": "已完成", "color_type": "success", "sort": 2, "is_builtin": True},

    # dict_msg_type (placeholder)
    {"dict_type": "dict_msg_type", "dict_value": "SYSTEM", "dict_label": "系统通知", "color_type": "primary", "sort": 1, "is_builtin": True},
    {"dict_type": "dict_msg_type", "dict_value": "TODO", "dict_label": "待办提醒", "color_type": "warning", "sort": 2, "is_builtin": True},
]


def seed_dicts(env: str, dry_run: bool = False) -> int:
    """
    Seed dictionary types and values.
    
    Rules per FP-H05-01:
    - Upsert by unique business key (dict_type, dict_value)
    - Does not overwrite admin-modified fields
    
    Returns:
        Number of records upserted
    """
    if dry_run:
        print(f"  Would seed {len(DICT_TYPES)} dict types")
        print(f"  Would seed {len(DICT_DATA)} dict values")
        return len(DICT_TYPES) + len(DICT_DATA)

    from app.db.session import get_db_session
    from app.domains.sys.models import DictData, DictType

    session = get_db_session()
    count = 0
    now = datetime.now()

    # Seed dict types
    for dt in DICT_TYPES:
        existing = session.query(DictType).filter(
            DictType.dict_type == dt["dict_type"],
            DictType.deleted == 0,
        ).first()

        if not existing:
            obj = DictType(
                tenant_id=1,
                dict_type=dt["dict_type"],
                name=dt["name"],
                status="ENABLED",
                creator=0,
                create_time=now,
            )
            session.add(obj)
            count += 1

    session.flush()

    # Seed dict data
    for dd in DICT_DATA:
        existing = session.query(DictData).filter(
            DictData.dict_type == dd["dict_type"],
            DictData.dict_value == dd["dict_value"],
            DictData.deleted == 0,
        ).first()

        if not existing:
            obj = DictData(
                tenant_id=1,
                dict_type=dd["dict_type"],
                dict_value=dd["dict_value"],
                dict_label=dd["dict_label"],
                color_type=dd.get("color_type", "neutral"),
                sort=dd.get("sort", 0),
                status="ENABLED",
                is_builtin=dd.get("is_builtin", False),
                creator=0,
                create_time=now,
            )
            session.add(obj)
            count += 1

    session.commit()
    return count
