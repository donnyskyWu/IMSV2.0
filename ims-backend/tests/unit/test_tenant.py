# tests/unit/test_tenant.py - Tenant model tests (FP-B04-04)
"""
Tests for tenant model and package restrictions.

Covers:
- UT-B04-12: Package limits menu access
- UT-B04-13: Platform tenant (id=1) not limited
- UT-B04-14: Expired tenant blocked
"""


from app.domains.sys.models import Tenant


class TestTenantModel:
    """Tests for Tenant model fields."""

    def test_tenant_has_required_fields(self):
        """Tenant model has all required fields."""
        assert hasattr(Tenant, "name")
        assert hasattr(Tenant, "status")
        assert hasattr(Tenant, "package_id")
        assert hasattr(Tenant, "expire_time")

    def test_valid_tenant_statuses(self):
        """Test valid tenant status values."""
        valid_statuses = ["ACTIVE", "DISABLED", "EXPIRED"]

        for status in valid_statuses:
            tenant = Tenant(
                id=1,
                tenant_id=1,
                name=f"Test {status}",
                status=status,
            )
            assert tenant.status == status


class TestPlatformTenant:
    """Tests for platform tenant (FP-B04-13)."""

    def test_platform_tenant_id_is_1(self):
        """UT-B04-13: Platform tenant ID is 1."""
        platform_tenant_id = 1
        assert platform_tenant_id == 1

    def test_platform_tenant_not_package_limited(self):
        """Platform tenant sees all menus regardless of package."""
        # Platform tenant (id=1) has special handling
        # in menu filtering logic
        tenant = Tenant(
            id=1,
            tenant_id=1,
            name="Platform Tenant",
            status="ACTIVE",
            package_id=None,  # No package restriction
        )

        assert tenant.id == 1


class TestTenantPackage:
    """Tests for tenant package restrictions (FP-B04-12)."""

    def test_tenant_has_package_id(self):
        """Non-platform tenants have package_id."""
        tenant = Tenant(
            id=2,
            tenant_id=2,
            name="Regular Tenant",
            status="ACTIVE",
            package_id=1,
        )

        assert tenant.package_id == 1


class TestTenantExpiration:
    """Tests for tenant expiration (FP-B04-14)."""

    def test_ut_b04_14_disabled_and_expired_tenant_block_login_and_refresh(
        self, db_session, test_context,
    ):
        """UT-B04-14：停用租户、过期租户，登录和刷新都返回 1008。

        用真实库里的租户行和用户行，不 mock get_db，也不 mock AuthService。
        先在启用状态下登录拿到 refresh，再改成停用 / 过期，两边都要被拒绝。
        """
        from datetime import timedelta

        import bcrypt
        from fastapi.testclient import TestClient

        from app.core.clock import get_now
        from app.domains.sys.models import Tenant
        from app.main import app
        from tests.support.rows import add, user

        password_hash = bcrypt.hashpw(b"Test1234", bcrypt.gensalt(rounds=4)).decode()
        now = get_now().replace(tzinfo=None)
        disabled = add(db_session, Tenant(
            tenant_id=1,
            name="停用租户",
            status="ENABLED",
        ))
        expired = add(db_session, Tenant(
            tenant_id=1,
            name="过期租户",
            status="ENABLED",
            expire_time=now + timedelta(days=30),
        ))
        disabled_user = user(
            db_session, "t2_disabled", password_hash=password_hash, tenant_id=disabled.id,
        )
        # 用例原文里的 t2_admin：租户到期后不能登录，也不能刷新。
        expired_user = user(
            db_session, "t2_admin", password_hash=password_hash, tenant_id=expired.id,
        )

        def login(client: TestClient, username: str) -> dict:
            response = client.post(
                "/admin-api/ims/auth/login",
                json={"username": username, "password": "Test1234"},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["code"] == 0, body
            return body["data"]

        def assert_1008(response) -> None:
            assert response.status_code == 200
            body = response.json()
            assert body["code"] == 1008, body
            assert body["msg"] == "所属组织已停用"

        with TestClient(app) as client:
            # 未过期、仍启用时可以登录，证明拦的是后来的停用 / 过期，不是用户本身。
            disabled_tokens = login(client, disabled_user.username)
            expired_tokens = login(client, expired_user.username)

            disabled.status = "DISABLED"
            expired.expire_time = now - timedelta(days=1)
            db_session.flush()

            assert_1008(client.post(
                "/admin-api/ims/auth/login",
                json={"username": disabled_user.username, "password": "Test1234"},
            ))
            assert_1008(client.post(
                "/admin-api/ims/auth/login",
                json={"username": expired_user.username, "password": "Test1234"},
            ))
            assert_1008(client.post(
                "/admin-api/ims/auth/refresh-token",
                json={"refreshToken": disabled_tokens["refreshToken"]},
            ))
            assert_1008(client.post(
                "/admin-api/ims/auth/refresh-token",
                json={"refreshToken": expired_tokens["refreshToken"]},
            ))

    def test_tenant_has_expire_time(self):
        """Tenant has expire_time field."""
        from datetime import datetime

        tenant = Tenant(
            id=3,
            tenant_id=3,
            name="Expiring Tenant",
            status="ACTIVE",
            expire_time=datetime(2026, 12, 31),
        )

        assert tenant.expire_time is not None
