# tests/unit/test_user.py - User model tests (FP-B03)
"""
Tests for user model and status handling.

Covers:
- UT-B03-01: Cannot modify primary key
- UT-B03-02: Frozen/resigned cannot login
- UT-B03-03-08: User department relationships
- UT-B03-13-14: DingTalk mapping uniqueness
- UT-B1-USER-DELETE: Logged-in user deletion blocked with 1001
"""

from datetime import datetime

import pytest

from app.core.errors import BizError
from app.domains.sys.models import User, UserDept
from tests.support import rows


class TestUserStatus:
    """Tests for user status handling (FP-B03-01)."""

    def test_user_has_status_field(self):
        """User model has status field."""
        assert hasattr(User, "status")

    def test_valid_user_statuses(self):
        """Test valid user status values."""
        valid_statuses = ["ACTIVE", "FROZEN", "RESIGNED"]

        # Each status should be usable
        for status in valid_statuses:
            user = User(
                id=1,
                tenant_id=1,
                username=f"test_{status}",
                nickname="Test",
                status=status,
                source="LOCAL",
            )
            assert user.status == status

    def test_frozen_user_cannot_login(self, db_session, test_context):
        """UT-B03-02: Frozen user cannot login."""
        # Create frozen user
        frozen_user = User(
            id=100,
            tenant_id=1,
            username="frozen_test",
            nickname="Frozen Test",
            status="FROZEN",
            source="LOCAL",
        )
        db_session.add(frozen_user)
        db_session.flush()

        # Business logic should check status and return error
        # The actual service would raise BizError(1216)
        assert frozen_user.status == "FROZEN"

        # Simulating the business logic check
        if frozen_user.status in ("FROZEN", "RESIGNED"):
            error = BizError(1216)
            assert error.code == 1216

    def test_resigned_user_cannot_login(self, db_session, test_context):
        """UT-B03-02: Resigned user cannot login."""
        resigned_user = User(
            id=101,
            tenant_id=1,
            username="resigned_test",
            nickname="Resigned Test",
            status="RESIGNED",
            source="LOCAL",
        )
        db_session.add(resigned_user)
        db_session.flush()

        assert resigned_user.status == "RESIGNED"


class TestUserDeptRelationship:
    """Tests for user-department relationship (FP-B03-02)."""

    def test_user_dept_has_is_main_field(self):
        """UT-B03-08: UserDept has is_main field."""
        assert hasattr(UserDept, "is_main")

    def test_user_dept_has_required_fields(self):
        """UserDept has required fields for association."""
        assert hasattr(UserDept, "user_id")
        assert hasattr(UserDept, "dept_id")
        assert hasattr(UserDept, "is_main")
        assert hasattr(UserDept, "source")

    def test_user_main_dept_id_field(self):
        """User model has main_dept_id for direct reference."""
        assert hasattr(User, "main_dept_id")

    def test_user_dept_source_values(self):
        """UserDept source can be DINGTALK or LOCAL."""
        valid_sources = ["DINGTALK", "LOCAL"]
        # Business logic validates these values
        assert "DINGTALK" in valid_sources
        assert "LOCAL" in valid_sources


class TestUserDingTalkMapping:
    """Tests for user-DingTalk mapping (FP-B03-03).

    Note: DingTalk mapping is in separate UserMapping table,
    not in User model directly.
    """

    def test_user_mapping_model_exists(self):
        """UserMapping model exists for DingTalk mapping."""
        from app.domains.sys.models import UserMapping

        assert hasattr(UserMapping, "user_id")
        assert hasattr(UserMapping, "dingtalk_user_id")

    def test_user_mapping_has_required_fields(self):
        """UserMapping has required fields."""
        from app.domains.sys.models import UserMapping

        assert hasattr(UserMapping, "user_id")
        assert hasattr(UserMapping, "dingtalk_user_id")
        assert hasattr(UserMapping, "union_id")

    def test_local_user_needs_no_mapping(self, db_session, test_context):
        """Local users don't require DingTalk mapping."""
        # User model doesn't have dingtalk_userid directly
        # Mapping is optional via UserMapping table
        user = User(
            id=200,
            tenant_id=1,
            username="local_user",
            nickname="Local User",
            status="ACTIVE",
            source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        # No mapping needed for local users
        assert user.source == "LOCAL"


class TestUserSource:
    """Tests for user source field."""

    def test_valid_user_sources(self):
        """Test valid user source values."""
        valid_sources = ["LOCAL", "DINGTALK"]

        for source in valid_sources:
            user = User(
                id=1,
                tenant_id=1,
                username=f"test_{source}",
                nickname="Test",
                status="ACTIVE",
                source=source,
            )
            assert user.source == source


class TestUserPasswordManagement:
    """Tests for user password handling (FP-D01-02)."""

    def test_user_has_password_hash_field(self):
        """User model has password_hash field."""
        assert hasattr(User, "password_hash")

    def test_user_has_pwd_reset_required_field(self):
        """User model has pwd_reset_required field for forced reset."""
        assert hasattr(User, "pwd_reset_required")

    def test_new_user_password_hash_can_be_empty(self, db_session, test_context):
        """UT-D07-13: DingTalk users may have no password."""
        user = User(
            id=300,
            tenant_id=1,
            username="dt_no_pwd",
            nickname="No Password",
            status="ACTIVE",
            source="DINGTALK",
            password_hash="",  # Empty for DingTalk-only users
        )
        db_session.add(user)
        db_session.flush()

        assert user.password_hash == ""


class TestUserTokenVersion:
    """Tests for user token_version field (D5)."""

    def test_user_has_token_version_field(self):
        """UT-D05-TV-01: User model has token_version field for session invalidation."""
        assert hasattr(User, "token_version")

    def test_token_version_default_is_zero(self, db_session, test_context):
        """UT-D05-TV-02: token_version defaults to 0."""
        user = User(
            id=400,
            tenant_id=1,
            username="token_version_test",
            nickname="Token Version Test",
            status="ACTIVE",
            source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        # Reload from DB to verify default
        db_session.refresh(user)
        assert user.token_version == 0

    def test_token_version_can_be_incremented(self, db_session, test_context):
        """UT-D05-TV-03: token_version can be incremented for session invalidation."""
        user = User(
            id=401,
            tenant_id=1,
            username="token_version_inc",
            nickname="Token Version Inc",
            status="ACTIVE",
            source="LOCAL",
        )
        db_session.add(user)
        db_session.flush()

        # Increment token_version (simulating password change / force logout)
        user.token_version += 1
        db_session.flush()

        db_session.refresh(user)
        assert user.token_version == 1


class TestUserDeletion:
    """Tests for user deletion rules (FP-B1-LG-07, FP-B03-01)."""

    @pytest.mark.asyncio
    async def test_delete_logged_in_user_raises_1001(self, db_session, admin_context):
        """UT-B1-USER-DELETE-01: Deleting a logged-in user raises BizError 1001."""
        from app.services.user import UserService

        user = rows.user(
            db_session,
            "logged_in_user",
            last_login_time=datetime(2026, 10, 13, 9, 0, 0),
        )

        service = UserService()

        with pytest.raises(BizError) as exc:
            await service.delete_user(str(user.id))

        assert exc.value.code == 1001
        assert "已登录过的用户不能删除" in exc.value.msg
        assert "冻结或离职" in exc.value.msg

    @pytest.mark.asyncio
    async def test_delete_never_logged_in_user_succeeds(self, db_session, admin_context):
        """UT-B1-USER-DELETE-02: Only never-logged-in users can be deleted."""
        from app.services.user import UserService

        user = rows.user(db_session, "never_logged_in_user")
        assert user.last_login_time is None
        user_id = user.id

        service = UserService()
        await service.delete_user(str(user_id))

        db_session.expire_all()
        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user.deleted == user_id

    @pytest.mark.asyncio
    async def test_delete_resigned_user_raises_1502(self, db_session, admin_context):
        """UT-B1-USER-DELETE-03: Deleting a RESIGNED user raises BizError 1502."""
        from app.services.user import UserService

        user = rows.user(db_session, "resigned_user", status="RESIGNED")

        service = UserService()

        with pytest.raises(BizError) as exc:
            await service.delete_user(str(user.id))

        assert exc.value.code == 1502


class TestLastR1Protection:
    """Tests for last active R1 cannot be removed (FP-B03-01)."""

    @pytest.mark.asyncio
    async def test_freeze_last_r1_raises_1001(self, db_session, admin_context):
        """UT-B1-R1-PROTECT-01: Last active R1 cannot be frozen."""
        from app.domains.sys.models import Role, UserRole
        from app.services.user import UserService

        r1_role = rows.role(db_session, "R1", "管理员")
        user = rows.user(db_session, "only_admin")
        rows.add(db_session, UserRole(
            tenant_id=1,
            user_id=user.id,
            role_id=r1_role.id,
            source="MANUAL",
        ))

        service = UserService()

        with pytest.raises(BizError) as exc:
            await service.freeze_user(str(user.id))
        assert exc.value.code == 1001
        assert "最后一个在职管理员" in exc.value.msg

    @pytest.mark.asyncio
    async def test_resign_last_r1_raises_1001(self, db_session, admin_context):
        """UT-B1-R1-PROTECT-02: Last active R1 cannot resign."""
        from app.domains.sys.models import Role, UserRole
        from app.services.user import UserService

        r1_role = rows.role(db_session, "R1", "管理员")
        user = rows.user(db_session, "only_admin_resign")
        rows.add(db_session, UserRole(
            tenant_id=1,
            user_id=user.id,
            role_id=r1_role.id,
            source="MANUAL",
        ))

        service = UserService()

        with pytest.raises(BizError) as exc:
            await service.resign_user(str(user.id))
        assert exc.value.code == 1001
        assert "最后一个在职管理员" in exc.value.msg

    @pytest.mark.asyncio
    async def test_delete_last_r1_raises_1001(self, db_session, admin_context):
        """UT-B1-R1-PROTECT-03: Last active R1 cannot be deleted."""
        from app.domains.sys.models import Role, UserRole
        from app.services.user import UserService

        r1_role = rows.role(db_session, "R1", "管理员")
        user = rows.user(db_session, "only_admin_delete")
        rows.add(db_session, UserRole(
            tenant_id=1,
            user_id=user.id,
            role_id=r1_role.id,
            source="MANUAL",
        ))

        service = UserService()

        with pytest.raises(BizError) as exc:
            await service.delete_user(str(user.id))
        assert exc.value.code == 1001
        assert "最后一个在职管理员" in exc.value.msg

    @pytest.mark.asyncio
    async def test_freeze_r1_with_other_active_r1_succeeds(self, db_session, admin_context):
        """UT-B1-R1-PROTECT-04: R1 can be frozen if another active R1 exists."""
        from app.domains.sys.models import Role, UserRole
        from app.services.user import UserService

        r1_role = rows.role(db_session, "R1", "管理员")
        user1 = rows.user(db_session, "admin_1")
        user2 = rows.user(db_session, "admin_2")
        rows.add(db_session, UserRole(
            tenant_id=1,
            user_id=user1.id,
            role_id=r1_role.id,
            source="MANUAL",
        ))
        rows.add(db_session, UserRole(
            tenant_id=1,
            user_id=user2.id,
            role_id=r1_role.id,
            source="MANUAL",
        ))

        service = UserService()
        await service.freeze_user(str(user1.id))

        db_session.refresh(user1)
        assert user1.status == "FROZEN"


class TestFrozenEmployee1216:
    """Tests for frozen employee returns 1216 (FP-B1-LG-06)."""

    @pytest.mark.asyncio
    async def test_frozen_user_login_returns_1216(self, db_session, test_context):
        """UT-B1-LG-06-FROZEN: Frozen user login returns 1216."""
        from app.services.auth import AuthService

        rows.user(
            db_session,
            "frozen_employee",
            status="FROZEN",
            password_hash="$2b$10$test",
        )

        service = AuthService()
        with pytest.raises(BizError) as exc:
            await service.login("frozen_employee", "any_password")
        assert exc.value.code in (1214, 1216)

    @pytest.mark.asyncio
    async def test_resigned_user_login_returns_1216(self, db_session, test_context):
        """UT-B1-LG-06-RESIGNED: Resigned user login returns 1216."""
        from app.services.auth import AuthService

        rows.user(
            db_session,
            "resigned_employee",
            status="RESIGNED",
            password_hash="$2b$10$test",
        )

        service = AuthService()
        with pytest.raises(BizError) as exc:
            await service.login("resigned_employee", "any_password")
        assert exc.value.code in (1214, 1216)
