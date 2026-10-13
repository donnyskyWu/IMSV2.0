# app/services/message.py - 消息服务（B3 新建，P0）
"""
消息服务实现。

功能：
- notify: 发送通知（站内信 + 钉钉推送，24h 去重）
- get_my_page: 我的消息分页
- get_my_detail: 消息详情
- mark_read: 标记已读（all or nothing）
- mark_all_read: 全部已读
- get_unread_count: 未读数
"""

import logging
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.cache import Cache
from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.domains.sys.models import InboxMessage

logger = logging.getLogger(__name__)

MESSAGE_DEDUP_TTL = 86400  # 24 hours


class ReadStatus:
    """消息已读状态。"""
    UNREAD = "UNREAD"
    READ = "READ"


def notify(
    session: Session,
    *,
    event_type: str,
    biz_key: str,
    receivers: list[int],
    title: str,
    content: str,
    route: Optional[str] = None,
    source_module: Optional[str] = None,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
    channels: Optional[list[str]] = None,
) -> list[InboxMessage]:
    """
    发送通知。

    - 站内信 + 钉钉推送
    - 24 小时去重
    """
    tenant_id = ctx.tenant_id
    messages = []

    for user_id in receivers:
        # 去重检查
        dedup_key = f"msg:{event_type}:{biz_key}:{user_id}"
        if Cache.get(dedup_key):
            logger.debug(f"消息去重跳过: {dedup_key}")
            continue

        # 创建站内信
        msg = InboxMessage(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            body=content,
            event_type=event_type,
            source_module=source_module,
            route=route,
            ref_type=ref_type,
            ref_id=ref_id,
            read_status=ReadStatus.UNREAD,
        )
        assign_pk(session, msg)
        session.add(msg)
        messages.append(msg)

        # 设置去重标记
        Cache.set(dedup_key, "1", MESSAGE_DEDUP_TTL)

        # 钉钉推送
        if channels and "dingtalk" in channels:
            _push_dingtalk_message(user_id, title, content)

    return messages


def get_my_page(
    session: Session,
    *,
    user_id: int,
    read_status: Optional[str] = None,
    keyword: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 20,
) -> dict:
    """
    我的消息分页。

    只返回本人消息。
    """
    tenant_id = ctx.tenant_id

    # 基础查询
    query = session.query(InboxMessage).filter(
        InboxMessage.tenant_id == tenant_id,
        InboxMessage.user_id == user_id,
        InboxMessage.deleted == 0,
    )

    # 已读状态筛选
    if read_status:
        query = query.filter(InboxMessage.read_status == read_status)

    # 关键字搜索
    if keyword:
        query = query.filter(
            or_(
                InboxMessage.title.contains(keyword),
                InboxMessage.body.contains(keyword),
            )
        )

    # 计数
    total = query.count()

    # 排序：按创建时间倒序
    query = query.order_by(InboxMessage.create_time.desc())

    # 分页
    offset = (page_no - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "pageNo": page_no,
        "pageSize": page_size,
        "list": [_message_to_dict(item) for item in items],
    }


def get_my_detail(
    session: Session,
    *,
    message_id: int,
    user_id: int,
) -> dict:
    """
    消息详情。

    他人/不存在 → 1504。
    """
    tenant_id = ctx.tenant_id

    msg = session.query(InboxMessage).filter(
        InboxMessage.id == message_id,
        InboxMessage.tenant_id == tenant_id,
        InboxMessage.user_id == user_id,
        InboxMessage.deleted == 0,
    ).first()

    if not msg:
        raise BizError(1504, "消息不存在或无权访问")

    return _message_to_dict(msg)


def mark_read(
    session: Session,
    *,
    user_id: int,
    ids: list[int],
) -> dict:
    """
    标记已读（all or nothing）。

    ids 中只要有一条不是本人的或不存在，整个请求返回 1504，一条都不改。
    """
    tenant_id = ctx.tenant_id

    if not ids:
        return {"updated": 0}

    # 先检查所有 id 是否都是本人的且存在
    messages = session.query(InboxMessage).filter(
        InboxMessage.id.in_(ids),
        InboxMessage.tenant_id == tenant_id,
        InboxMessage.deleted == 0,
    ).all()

    # 检查数量是否匹配
    if len(messages) != len(ids):
        raise BizError(1504, "部分消息不存在")

    # 检查是否都是本人的
    for msg in messages:
        if msg.user_id != user_id:
            raise BizError(1504, "部分消息不属于当前用户")

    # 标记已读
    now = get_now()
    updated = 0
    for msg in messages:
        if msg.read_status == ReadStatus.UNREAD:
            msg.read_status = ReadStatus.READ
            msg.read_time = now
            updated += 1

    return {"updated": updated}


def mark_all_read(
    session: Session,
    *,
    user_id: int,
) -> dict:
    """
    全部已读。

    返回 {updated}。
    """
    tenant_id = ctx.tenant_id
    now = get_now()

    # 批量更新
    result = session.query(InboxMessage).filter(
        InboxMessage.tenant_id == tenant_id,
        InboxMessage.user_id == user_id,
        InboxMessage.read_status == ReadStatus.UNREAD,
        InboxMessage.deleted == 0,
    ).update({
        InboxMessage.read_status: ReadStatus.READ,
        InboxMessage.read_time: now,
    }, synchronize_session=False)

    return {"updated": result}


def get_unread_count(
    session: Session,
    *,
    user_id: int,
) -> int:
    """
    未读数。

    返回本人未读消息数。
    """
    tenant_id = ctx.tenant_id

    count = session.query(InboxMessage).filter(
        InboxMessage.tenant_id == tenant_id,
        InboxMessage.user_id == user_id,
        InboxMessage.read_status == ReadStatus.UNREAD,
        InboxMessage.deleted == 0,
    ).count()

    return count


def _message_to_dict(msg: InboxMessage) -> dict:
    """将 InboxMessage 转为字典。"""
    return {
        "id": str(msg.id),
        "title": msg.title,
        "body": msg.body,
        "eventType": msg.event_type,
        "sourceModule": msg.source_module,
        "route": msg.route,
        "refType": msg.ref_type,
        "refId": str(msg.ref_id) if msg.ref_id else None,
        "readStatus": msg.read_status,
        "readTime": msg.read_time.isoformat() if msg.read_time else None,
        "createTime": msg.create_time.isoformat() if msg.create_time else None,
    }


def _push_dingtalk_message(user_id: int, title: str, content: str) -> None:
    """钉钉推送消息。"""
    # TODO: 实际调用钉钉推送 API
    logger.info(f"钉钉推送消息: user={user_id}, title={title}")
