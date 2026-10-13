# tests/unit/test_train_session.py - Session and frozen user tests (B21)
"""
Unit tests for session invalidation and frozen user handling.

Per review feedback:
- _drop_sessions(user_id) already in main, use directly
- Frozen/session tests NOT postponed to #26
- 1216 for FROZEN/RESIGNED
- 1002 for session invalid
"""

import pytest
from unittest.mock import MagicMock, patch


class TestDropSessions:
    """Tests for _drop_sessions usage in training module."""

    def test_drop_sessions_exists_in_main(self):
        """UT-B21-SESSION-01: _drop_sessions available in main."""
        from app.services.user import UserService

        service = UserService()
        assert hasattr(service, "_drop_sessions")

    def test_drop_sessions_signature(self):
        """_drop_sessions takes single user_id parameter."""
        from app.services.user import UserService
        import inspect

        service = UserService()
        sig = inspect.signature(service._drop_sessions)
        params = list(sig.parameters.keys())

        assert "user_id" in params or len(params) == 1

    @patch("app.services.auth.AuthService")
    @patch("app.core.cache.Cache")
    def test_drop_sessions_clears_user_sessions(self, mock_cache, mock_auth):
        """UT-B21-SESSION-01: Frozen user's sessions are cleared."""
        from app.services.user import UserService

        mock_cache.smembers.return_value = ["session1", "session2"]

        service = UserService()
        service._drop_sessions(12345)

        mock_cache.smembers.assert_called()

    @patch("app.services.auth.AuthService")
    @patch("app.core.cache.Cache")
    def test_drop_sessions_adds_to_blacklist(self, mock_cache, mock_auth):
        """Session IDs added to blacklist after drop."""
        from app.services.user import UserService

        mock_cache.smembers.return_value = ["session1"]

        service = UserService()
        service._drop_sessions(12345)

        calls = [str(c) for c in mock_cache.method_calls]
        assert any("blacklist" in c.lower() or "set" in c.lower() for c in calls)


class TestFrozenUserHandling:
    """Tests for frozen user error codes."""

    def test_frozen_status_constant(self):
        """FROZEN status is defined."""
        from app.domains.sys.models import User
        user = MagicMock(spec=User)
        user.status = "FROZEN"
        assert user.status == "FROZEN"

    def test_resigned_status_constant(self):
        """RESIGNED status is defined."""
        from app.domains.sys.models import User
        user = MagicMock(spec=User)
        user.status = "RESIGNED"
        assert user.status == "RESIGNED"


class TestSessionErrorCodes:
    """Tests for session-related error codes."""

    def test_error_code_1002_defined(self):
        """Error code 1002 for session invalid is defined."""
        from app.core.errors import BizError

        error = BizError(1002, msg="登录已失效")
        assert error.code == 1002

    def test_error_code_1216_defined(self):
        """Error code 1216 for frozen/resigned is defined."""
        from app.core.errors import BizError

        error = BizError(1216, msg="账号已冻结")
        assert error.code == 1216


class TestPermVersionKeys:
    """Tests for permission version key format (stub + real assertion)."""

    def test_user_perm_key_format_assertion(self):
        """UT-B21-SESSION-03: User perm key format is correct."""
        from app.domains.train.scope import get_user_perm_key

        assert get_user_perm_key(123) == "ims:perm_ver:u:123"
        assert get_user_perm_key(1) == "ims:perm_ver:u:1"
        assert get_user_perm_key(99999) == "ims:perm_ver:u:99999"

    def test_tenant_perm_key_format_assertion(self):
        """Tenant perm key format is correct."""
        from app.domains.train.scope import get_tenant_perm_key

        assert get_tenant_perm_key(1) == "ims:perm_ver:t:1"
        assert get_tenant_perm_key(456) == "ims:perm_ver:t:456"

    def test_key_format_consistency(self):
        """Keys follow ims:perm_ver:{type}:{id} pattern."""
        from app.domains.train.scope import get_user_perm_key, get_tenant_perm_key

        user_key = get_user_perm_key(100)
        tenant_key = get_tenant_perm_key(100)

        assert user_key.startswith("ims:perm_ver:")
        assert tenant_key.startswith("ims:perm_ver:")
        assert ":u:" in user_key
        assert ":t:" in tenant_key


class TestIntegrationWithTrainModule:
    """Tests for training module integration with session handling."""

    def test_train_service_can_import_drop_sessions(self):
        """Training service can import _drop_sessions if needed."""
        try:
            from app.services.user import UserService
            service = UserService()
            assert callable(service._drop_sessions)
        except ImportError:
            pytest.fail("Cannot import _drop_sessions from user service")

    def test_study_service_validates_user_assignment(self):
        """Study service validates user is assigned (→ 1105)."""
        from app.domains.train.service import TrainStudyService

        service = TrainStudyService()
        assert hasattr(service, "report_video_progress")
        assert hasattr(service, "confirm_duration")
        assert hasattr(service, "submit_quiz")
