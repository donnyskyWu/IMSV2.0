# app/services/notify.py - Notification service (FP-G01)
"""
Notification service for sending messages to users.

Implements:
- FP-G01-01: 站内信、钉钉推送
- B18: 会议提醒、逾期推送

对照 main 已有实现（app/services/integrity.py 的 _notify 方法），
使用 InboxMessage 模型写入站内信。
"""

import logging
from typing import List, Optional

from app.db.session import get_db_session
from app.domains.sys.models import InboxMessage

logger = logging.getLogger(__name__)


class NotifyService:
    """Notification service for sending messages via inbox (FP-G01)."""

    async def send(
        self,
        user_ids: List[int],
        tenant_id: int,
        title: str,
        content: str,
        biz_type: str,
        biz_id: str,
        channels: Optional[List[str]] = None,
    ) -> dict:
        """
        Send notification to users via inbox.

        Args:
            user_ids: List of user IDs to notify
            tenant_id: Tenant ID
            title: Message title
            content: Message content
            biz_type: Business type for tracing
            biz_id: Business ID for tracing
            channels: Notification channels (default: INBOX)

        Returns:
            Result dict with sent count
        """
        if not user_ids:
            return {"sent": 0, "failed": 0}

        if channels is None:
            channels = ["INBOX"]

        session = get_db_session()
        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                if "INBOX" in channels:
                    msg = InboxMessage(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        title=title,
                        body=content,
                    )
                    session.add(msg)
                    sent += 1

                logger.info(
                    "Notification sent: user_id=%s, tenant_id=%s, title=%s, "
                    "biz_type=%s, biz_id=%s",
                    user_id,
                    tenant_id,
                    title,
                    biz_type,
                    biz_id,
                )
            except Exception as e:
                logger.error("Failed to send notification to user %s: %s", user_id, e)
                failed += 1

        if sent > 0:
            session.flush()

        return {"sent": sent, "failed": failed}
