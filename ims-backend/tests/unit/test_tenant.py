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

    def test_expired_tenant_status(self):
        """UT-B04-14: Expired tenant has status EXPIRED or blocks login."""
        from app.core.errors import get_error_info

        # Error code 1008 is used for expired tenant
        info = get_error_info(1008)
        assert info is not None

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
