# app/integrations/dingtalk/client.py - DingTalk client (FP-H04-01)
"""
DingTalk API client.

Per FP-D02-02 and FP-D07:
- Exchange auth code for user info
- List departments
- List users
"""

from dataclasses import dataclass
from typing import Any, Optional

from app.integrations.base import BaseAdapter


@dataclass
class DingTalkUser:
    """DingTalk user info."""
    user_id: str
    union_id: Optional[str]
    name: str
    mobile: Optional[str]
    dept_ids: list[int]


@dataclass
class DingTalkDept:
    """DingTalk department info."""
    dept_id: int
    name: str
    parent_id: int


class DingTalkClient(BaseAdapter[Any]):
    """
    DingTalk IMS application client.

    Mode: real or mock
    Error codes: 5003 (timeout), 1006 (API error)
    """

    @property
    def system_name(self) -> str:
        return "钉钉"

    @property
    def error_code_timeout(self) -> int:
        return 5003

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        mode: str = "mock",
    ):
        super().__init__(mode=mode)
        self.app_key = app_key
        self.app_secret = app_secret
        self._access_token: Optional[str] = None

        # Mock data
        self._mock_user = DingTalkUser(
            user_id="mock_dingtalk_user_001",
            union_id="mock_union_001",
            name="测试用户",
            mobile="13800138000",
            dept_ids=[1],
        )
        self._mock_depts = [
            DingTalkDept(dept_id=1, name="公司", parent_id=0),
        ]

    async def _call_real(self, *args, **kwargs) -> Any:
        """Make real DingTalk API call."""
        raise NotImplementedError("Real DingTalk API not implemented")

    async def _call_mock(self, *args, **kwargs) -> Any:
        """Return mock response."""
        return None

    async def get_user_by_auth_code(self, auth_code: str) -> DingTalkUser:
        """
        Exchange auth code for user info.

        Per FP-D02-02:
        - Called during SSO callback
        - Returns userid, unionid, mobile
        """
        if self.mode == "mock":
            return self._mock_user

        # Real implementation would:
        # 1. Get access token
        # 2. Call /topapi/v2/user/getuserinfo with auth_code
        # 3. Call /topapi/v2/user/get for full user info
        raise NotImplementedError("Real DingTalk API not implemented")

    async def list_departments(self) -> list[DingTalkDept]:
        """
        List all departments.

        Per FP-D07-04:
        - Used for organization sync
        """
        if self.mode == "mock":
            return self._mock_depts

        raise NotImplementedError("Real DingTalk API not implemented")

    async def list_users(self, dept_id: int) -> list[DingTalkUser]:
        """
        List users in a department.

        Per FP-D07-04:
        - Used for organization sync
        """
        if self.mode == "mock":
            if dept_id == 1:
                return [self._mock_user]
            return []

        raise NotImplementedError("Real DingTalk API not implemented")

    async def send_work_notification(
        self,
        user_ids: list[str],
        title: str,
        content: str,
    ) -> bool:
        """
        Send work notification.

        Per FP-G01-01:
        - Used for message notifications
        - Respects dingtalk.notify.enabled parameter
        """
        if self.mode == "mock":
            return True

        raise NotImplementedError("Real DingTalk API not implemented")

    def set_mock_user(self, user: DingTalkUser) -> None:
        """Set mock user for testing."""
        self._mock_user = user

    def set_mock_depts(self, depts: list[DingTalkDept]) -> None:
        """Set mock departments for testing."""
        self._mock_depts = depts
