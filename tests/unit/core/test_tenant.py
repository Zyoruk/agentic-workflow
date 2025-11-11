"""Tests for tenant management system."""

import pytest
from datetime import datetime

from agentic_workflow.core.tenant import (
    Tenant,
    TenantPreference,
    TenantService,
    TenantStatus,
    TenantUsage,
    TierType,
    get_tenant_service,
)


class TestTenant:
    """Tests for Tenant model."""

    def test_create_tenant(self):
        """Test creating a tenant."""
        tenant = Tenant(
            name="Acme Corp",
            tier=TierType.STANDARD,
        )

        assert tenant.name == "Acme Corp"
        assert tenant.tier == TierType.STANDARD
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.id is not None
        assert isinstance(tenant.created_at, datetime)

    def test_tenant_has_feature(self):
        """Test checking if tenant has a feature."""
        tenant = Tenant(name="Test", tier=TierType.FREE)
        
        assert tenant.has_feature("planning")
        assert not tenant.has_feature("file_attachments")

    def test_tenant_can_use_agent(self):
        """Test checking if tenant can use an agent."""
        tenant = Tenant(name="Test", tier=TierType.STANDARD)
        
        assert tenant.can_use_agent("planning")
        assert tenant.can_use_agent("code_generation")
        assert not tenant.can_use_agent("cicd")

    def test_tenant_get_limits(self):
        """Test getting tenant limits."""
        tenant = Tenant(name="Test", tier=TierType.BUSINESS)
        limits = tenant.get_limits()

        assert limits.max_prompt_size == 500000
        assert limits.requests_per_day == 10000
        assert limits.file_attachments is True
        assert limits.audit_logging is True


class TestTenantPreference:
    """Tests for TenantPreference model."""

    def test_create_preference(self):
        """Test creating a preference."""
        preference = TenantPreference(
            tenant_id="test-tenant",
            preference_key="default_model",
            preference_value={"model": "gpt-4", "temperature": 0.7},
        )

        assert preference.tenant_id == "test-tenant"
        assert preference.preference_key == "default_model"
        assert preference.preference_value["model"] == "gpt-4"
        assert isinstance(preference.created_at, datetime)


class TestTenantUsage:
    """Tests for TenantUsage model."""

    def test_create_usage(self):
        """Test creating usage record."""
        usage = TenantUsage(tenant_id="test-tenant")

        assert usage.tenant_id == "test-tenant"
        assert usage.requests_count == 0
        assert usage.tokens_used == 0

    def test_is_over_quota(self):
        """Test quota checking."""
        usage = TenantUsage(tenant_id="test-tenant", requests_count=60)
        
        tenant = Tenant(name="Test", tier=TierType.FREE)
        limits = tenant.get_limits()

        assert usage.is_over_quota(limits) is True

        usage.requests_count = 40
        assert usage.is_over_quota(limits) is False

    def test_get_quota_status(self):
        """Test getting quota status."""
        usage = TenantUsage(
            tenant_id="test-tenant",
            requests_count=25,
            tokens_used=1000,
        )
        
        tenant = Tenant(name="Test", tier=TierType.FREE)
        limits = tenant.get_limits()
        status = usage.get_quota_status(limits)

        assert status["requests"]["used"] == 25
        assert status["requests"]["limit"] == 50
        assert status["requests"]["percentage"] == 50.0


@pytest.mark.asyncio
class TestTenantService:
    """Tests for TenantService."""

    async def test_create_tenant(self):
        """Test creating a tenant via service."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
            metadata={"industry": "technology"},
        )

        assert tenant.name == "Test Corp"
        assert tenant.tier == TierType.STANDARD
        assert tenant.metadata["industry"] == "technology"

    async def test_create_duplicate_tenant(self):
        """Test creating duplicate tenant fails."""
        service = TenantService()
        await service.create_tenant(name="Test Corp")

        with pytest.raises(ValueError, match="already exists"):
            await service.create_tenant(name="Test Corp")

    async def test_get_tenant(self):
        """Test getting a tenant."""
        service = TenantService()
        created = await service.create_tenant(name="Test Corp")

        retrieved = await service.get_tenant(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    async def test_get_nonexistent_tenant(self):
        """Test getting nonexistent tenant."""
        service = TenantService()
        tenant = await service.get_tenant("nonexistent")
        assert tenant is None

    async def test_list_tenants(self):
        """Test listing tenants."""
        service = TenantService()
        await service.create_tenant(name="Corp A", tier=TierType.FREE)
        await service.create_tenant(name="Corp B", tier=TierType.STANDARD)

        tenants = await service.list_tenants()
        assert len(tenants) == 2

    async def test_list_tenants_filtered(self):
        """Test listing tenants with filters."""
        service = TenantService()
        await service.create_tenant(name="Corp A", tier=TierType.FREE)
        await service.create_tenant(name="Corp B", tier=TierType.STANDARD)

        free_tenants = await service.list_tenants(tier=TierType.FREE)
        assert len(free_tenants) == 1
        assert free_tenants[0].tier == TierType.FREE

    async def test_update_tenant(self):
        """Test updating a tenant."""
        service = TenantService()
        tenant = await service.create_tenant(name="Test Corp")

        updated = await service.update_tenant(
            tenant.id,
            name="Updated Corp",
            tier=TierType.BUSINESS,
        )

        assert updated is not None
        assert updated.name == "Updated Corp"
        assert updated.tier == TierType.BUSINESS

    async def test_delete_tenant(self):
        """Test deleting a tenant."""
        service = TenantService()
        tenant = await service.create_tenant(name="Test Corp")

        deleted = await service.delete_tenant(tenant.id)
        assert deleted is True

        retrieved = await service.get_tenant(tenant.id)
        assert retrieved is None

    async def test_set_preference(self):
        """Test setting a preference."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,  # Allows preferences
        )

        preference = await service.set_preference(
            tenant.id,
            "default_model",
            {"model": "gpt-4"},
        )

        assert preference is not None
        assert preference.preference_key == "default_model"
        assert preference.preference_value["model"] == "gpt-4"

    async def test_set_preference_free_tier_fails(self):
        """Test setting preference for free tier fails."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.FREE,  # No preferences allowed
        )

        with pytest.raises(ValueError, match="does not support preference storage"):
            await service.set_preference(
                tenant.id,
                "default_model",
                {"model": "gpt-4"},
            )

    async def test_get_preference(self):
        """Test getting a preference."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        await service.set_preference(
            tenant.id,
            "default_model",
            {"model": "gpt-4"},
        )

        preference = await service.get_preference(tenant.id, "default_model")
        assert preference is not None
        assert preference.preference_value["model"] == "gpt-4"

    async def test_get_all_preferences(self):
        """Test getting all preferences."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        await service.set_preference(tenant.id, "pref1", {"value": 1})
        await service.set_preference(tenant.id, "pref2", {"value": 2})

        preferences = await service.get_all_preferences(tenant.id)
        assert len(preferences) == 2
        assert "pref1" in preferences
        assert "pref2" in preferences

    async def test_delete_preference(self):
        """Test deleting a preference."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        await service.set_preference(tenant.id, "test_pref", {"value": 1})
        deleted = await service.delete_preference(tenant.id, "test_pref")
        assert deleted is True

        preference = await service.get_preference(tenant.id, "test_pref")
        assert preference is None

    async def test_track_usage(self):
        """Test tracking usage."""
        service = TenantService()
        tenant = await service.create_tenant(name="Test Corp")

        usage = await service.track_usage(
            tenant.id,
            requests=5,
            tokens=1000,
        )

        assert usage is not None
        assert usage.requests_count == 5
        assert usage.tokens_used == 1000

    async def test_get_usage(self):
        """Test getting usage."""
        service = TenantService()
        tenant = await service.create_tenant(name="Test Corp")

        await service.track_usage(tenant.id, requests=10)
        usage = await service.get_usage(tenant.id)

        assert usage is not None
        assert usage.requests_count == 10

    async def test_check_quota_allowed(self):
        """Test quota check when allowed."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.FREE,
        )

        await service.track_usage(tenant.id, requests=10)
        result = await service.check_quota(tenant.id)

        assert result["allowed"] is True

    async def test_check_quota_exceeded(self):
        """Test quota check when exceeded."""
        service = TenantService()
        tenant = await service.create_tenant(
            name="Test Corp",
            tier=TierType.FREE,
        )

        await service.track_usage(tenant.id, requests=60)
        result = await service.check_quota(tenant.id)

        assert result["allowed"] is False
        assert "exceeded" in result["reason"]

    async def test_check_quota_suspended_tenant(self):
        """Test quota check for suspended tenant."""
        service = TenantService()
        tenant = await service.create_tenant(name="Test Corp")
        await service.update_tenant(tenant.id, status=TenantStatus.SUSPENDED)

        result = await service.check_quota(tenant.id)

        assert result["allowed"] is False
        assert "status" in result["reason"]

    def test_get_tier_info(self):
        """Test getting tier information."""
        service = TenantService()
        tier_info = service.get_tier_info(TierType.BUSINESS)

        assert tier_info.name == TierType.BUSINESS
        assert "monitoring" in tier_info.features
        assert tier_info.limits.max_prompt_size == 500000

    def test_list_all_tiers(self):
        """Test listing all tiers."""
        service = TenantService()
        tiers = service.list_all_tiers()

        assert len(tiers) == 3
        tier_names = [t.name for t in tiers]
        assert TierType.FREE in tier_names
        assert TierType.STANDARD in tier_names
        assert TierType.BUSINESS in tier_names


def test_get_tenant_service():
    """Test getting tenant service singleton."""
    service1 = get_tenant_service()
    service2 = get_tenant_service()

    assert service1 is service2
