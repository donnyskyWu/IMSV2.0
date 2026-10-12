# app/services/b1_schema_backfill.py - B1 迁移历史回填（FP-B1-BG-08）
"""把已有岗位规则、钉钉自动角色和同步事件补到 B1 新列上。

版本: v1.0
日期: 2026-10-12

只填空值，不覆盖已经写过的 rule_id、rule_name、biz_type。
可重复执行。新库没有历史行时返回全 0。
"""

from typing import Any

# 钉钉事件类型 → BG-01 biz_type。
# 人员变更先记 USER_UPDATE；TRANSFER 只在处理时判定，回填不把变更写成调岗。
# 不在表内的 event_type 保持空，不猜测别名。
EVENT_BIZ_TYPES = {
    "user_add_org": "HIRE",
    "user_modify_org": "USER_UPDATE",
    "user_leave_org": "RESIGN",
    "org_dept_create": "DEPT_CREATE",
    "org_dept_modify": "DEPT_UPDATE",
    "org_dept_remove": "DEPT_DELETE",
    "HIRE": "HIRE",
    "TRANSFER": "TRANSFER",
    "USER_UPDATE": "USER_UPDATE",
    "RESIGN": "RESIGN",
    "DEPT_CREATE": "DEPT_CREATE",
    "DEPT_UPDATE": "DEPT_UPDATE",
    "DEPT_DELETE": "DEPT_DELETE",
}


def _same_tenant(row_tenant: int, expected: int) -> bool:
    """同一租户。比较的是入参，不在查询条件里写租户字段。"""
    return row_tenant == expected


def backfill_b1_foundations(session: Any) -> dict[str, int]:
    """执行全部回填。返回各类补上的行数。"""
    filled = {
        "user_roles": _backfill_user_roles(session),
        "rule_versions": _backfill_rule_versions(session),
        "events": _backfill_event_biz_types(session),
    }
    session.flush()
    return filled


def _backfill_user_roles(session: Any) -> int:
    """DINGTALK_AUTO 且 rule_id 为空时，按用户岗位找到规则并写 rule_id、rule_version=1。"""
    from app.domains.sys.models import PositionRoleRule, User, UserRole

    links = session.query(UserRole).all()
    rules = session.query(PositionRoleRule).filter(PositionRoleRule.deleted == 0).all()
    count = 0
    for link in links:
        if link.source != "DINGTALK_AUTO" or link.rule_id is not None:
            continue
        user = session.query(User).filter(User.id == link.user_id).first()
        if user is None or not user.position_code:
            continue
        chosen = _pick_rule(rules, user.tenant_id, user.position_code)
        if chosen is None:
            continue
        link.rule_id = chosen.id
        if link.rule_version is None:
            link.rule_version = 1
        count += 1
    return count


def _pick_rule(rules: list[Any], tenant_id: int, position_code: str) -> Any:
    """同一岗位多条规则时，优先启用且未归档，其次版本高，再按 id。"""
    matched = [
        rule for rule in rules
        if rule.position_code == position_code
        and rule.deleted == 0
        and _same_tenant(rule.tenant_id, tenant_id)
    ]
    if not matched:
        return None

    def sort_key(rule: Any) -> tuple[int, int, int]:
        enabled = 0 if rule.status == "ENABLED" and not rule.archived else 1
        return (enabled, -int(rule.version or 0), int(rule.id or 0))

    matched.sort(key=sort_key)
    return matched[0]


def _position_label(session: Any, position_code: str) -> str:
    """岗位中文名。字典没有时用岗位编码，不发明别的名称。"""
    from app.domains.sys.models import DictData

    row = session.query(DictData).filter(
        DictData.dict_type == "dict_position",
        DictData.dict_value == position_code,
        DictData.deleted == 0,
    ).first()
    if row is not None and row.dict_label:
        return row.dict_label
    return position_code


def _backfill_rule_versions(session: Any) -> int:
    """已有规则补一条 v1。rule_name 为空时写成岗位名称。"""
    from app.domains.sys.models import PositionRoleRule, PositionRuleVersion

    rules = session.query(PositionRoleRule).filter(PositionRoleRule.deleted == 0).all()
    count = 0
    for rule in rules:
        if not rule.rule_name:
            rule.rule_name = _position_label(session, rule.position_code)
        exists = session.query(PositionRuleVersion).filter(
            PositionRuleVersion.rule_id == rule.id,
            PositionRuleVersion.version == 1,
            PositionRuleVersion.deleted == 0,
        ).first()
        if exists is not None:
            continue
        session.add(PositionRuleVersion(
            tenant_id=rule.tenant_id,
            rule_id=rule.id,
            version=1,
            rule_name=rule.rule_name,
            main_role_id=rule.role_id,
            description=rule.description,
            status=rule.status,
            change_type="CREATE",
            operator_id=None,
        ))
        count += 1
    return count


def _backfill_event_biz_types(session: Any) -> int:
    """已有事件按已知钉钉事件类型回填 biz_type。未知类型跳过。"""
    from app.domains.sys.models import OrgSyncEvent

    events = session.query(OrgSyncEvent).filter(OrgSyncEvent.deleted == 0).all()
    count = 0
    for event in events:
        if event.biz_type:
            continue
        mapped = EVENT_BIZ_TYPES.get(event.event_type or "")
        if mapped is None:
            continue
        event.biz_type = mapped
        count += 1
    return count
