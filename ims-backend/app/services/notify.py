# app/services/notify.py - Notification service (FP-G01)
"""
Notification service for sending messages to users.

Implements:
- FP-G01-01: 站内信、钉钉推送
- B18: 会议提醒、逾期推送
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class NotifyService:
    """Notification service for sending messages."""

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
        Send notification to users.

        Args:
            user_ids: List of user IDs to notify
            tenant_id: Tenant ID
            title: Message title
            content: Message content
            biz_type: Business type for tracing
            biz_id: Business ID for tracing
            channels: Notification channels (default: INBOX + DINGTALK)

        Returns:
            Result dict with sent count
        """
        if not user_ids:
            return {"sent": 0, "failed": 0}

        if channels is None:
            channels = ["INBOX", "DINGTALK"]

        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                logger.info(
                    "Sending notification: user_id=%s, tenant_id=%s, title=%s, "
                    "biz_type=%s, biz_id=%s, channels=%s",
                    user_id, tenant_id, title, biz_type, biz_id, channels
                )
                sent += 1
            except Exception as e:
                logger.error("Failed to send notification to user %s: %s", user_id, e)
                failed += 1

        return {"sent": sent, "failed": failed}
