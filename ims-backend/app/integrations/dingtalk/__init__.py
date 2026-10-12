# app/integrations/dingtalk - DingTalk IMS app adapter (FW-H04)
"""
DingTalk IMS application integration.

Used for:
- User authentication (SSO callback)
- Organization sync
- Work notifications

Error codes:
- 5003: DingTalk timeout or unavailable
- 1006: DingTalk API error
"""

from app.integrations.dingtalk.client import DingTalkClient

__all__ = ["DingTalkClient"]
