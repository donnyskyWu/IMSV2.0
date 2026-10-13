# 站内消息最小实现（B5，B3 未合入时使用）。版本 v1.0 · 2026-10-13
"""notify 写入 ims_sys_inbox，不另建消息表。"""

from __future__ import annotations

from app.db.session import get_db_session
from app.domains.sys.models import InboxMessage
from app.services.corp_support import add_row


def notify(user_id: int, title: str, body: str = "", scene: str = "") -> InboxMessage:
    """给一个用户写一条站内信。scene 记在正文前缀，避免再加列。"""
    text = body or ""
    if scene:
        text = f"[{scene}] {text}".strip()
    row = InboxMessage(user_id=int(user_id), title=title, body=text)
    return add_row(get_db_session(), row)
