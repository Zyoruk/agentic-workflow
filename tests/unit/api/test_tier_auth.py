"""Tests for tier-based authentication and authorization."""

import pytest
from fastapi import HTTPException
from unittest.mock import Mock, AsyncMock

from agentic_workflow.api.tier_auth import (
    TierAuthMiddleware,
    FeatureGate,
    require_tier,
    require_feature,
    require_agent,
)
from agentic_workflow.core.tenant import (
    Tenant,
    TenantService,
    TierType,
    TenantStatus,
    get_tenant_service,
)


@pytest.mark.asyncio
class TestTierAuthMiddleware:
    """Test suite for tier authentication middleware."""

    async def test_get_tenant_from_header(self):
        """Test extracting tenant ID from request header."""
        tenant_service = get_tenant_service()
        middleware = TierAuthMiddleware(tenant_service=tenant_service)

        # Create a tenant
        tenant = await tenant_service.create_tenant(
            name="Test Corp",
            tier=TierType.STANDARD,
        )

        # Mock request with header
        request = Mock()
        request.headers = {"X-Tenant-ID": tenant.id}
        request.query_params = {}
        request.method = "GET"

        extracted_tenant = await middleware.get_tenant_from_request(request)

        assert extracted_tenant is not None
        assert extracted_tenant.id == tenant.id
        assert extracted_tenant.name == "Test Corp"

    async def test_get_tenant_from_query_param(self):
        """Test extracting tenant ID from query parameter."""
        tenant_service = get_tenant_service()
        middleware = TierAuthMiddleware(tenant_service=tenant_service)

        tenant = await tenant_service.create_tenant(
            name="Query Test",
            tier=TierType.FREE,
        )

        request = Mock()
        request.headers = {}
        request.query_params = {"tenant_id": tenant.id}
        request.method = "GET"

        extracted_tenant = await middleware.get_tenant_from_request(request)

        assert extracted_tenant is not None
        assert extracted_tenant.id == tenant.id

    async def test_inactive_tenant_denied(self):
        """Test that inactive tenants are denied access."""
        tenant_service = get_tenant_service()
        middleware = TierAuthMiddleware(tenant_service=tenant_service)

        tenant = await tenant_service.create_tenant(
            name="Inactive Corp",
            tier=TierType.BUSINESS,
        )

        # Suspend tenant
        await tenant_service.update_tenant(
            tenant_id=tenant.id,
            status=TenantStatus.SUSPENDED,
        )

        request = Mock()
        request.headers = {"X-Tenant-ID": tenant.id}
        request.query_params = {}
        request.method = "GET"

        with pytest.raises(HTTPException) as exc_info:
            await middleware(request)

        assert exc_info.value.status_code == 403

    async def test_no_tenant_id_raises_error(self):
        """Test that missing tenant ID raises 401."""
        tenant_service = get_tenant_service()
        middleware = TierAuthMiddleware(tenant_service=tenant_service)

        request = Mock()
        request.headers = {}
        request.query_params = {}
        request.method = "GET"

        with pytest.raises(HTTPException) as exc_info:
            await middleware(request)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestRequireTier:
    """Test suite for tier requirement decorator."""

    async def test_require_tier_passes(self):
        """Test tier requirement passes for correct tier."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Business User {id(self)}",
            tier=TierType.BUSINESS,
        )

        # Create dependency function
        dep_func = require_tier(TierType.BUSINESS, TierType.STANDARD)

        # Should not raise
        result = await dep_func(tenant=tenant)
        assert result.id == tenant.id

    async def test_require_tier_fails(self):
        """Test tier requirement fails for insufficient tier."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        dep_func = require_tier(TierType.BUSINESS)

        with pytest.raises(HTTPException) as exc_info:
            await dep_func(tenant=tenant)

        assert exc_info.value.status_code == 403
        assert "business" in exc_info.value.detail.lower()


@pytest.mark.asyncio
class TestRequireFeature:
    """Test suite for feature requirement decorator."""

    async def test_require_feature_passes(self):
        """Test feature requirement passes when feature available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Standard User {id(self)}",
            tier=TierType.STANDARD,
        )

        dep_func = require_feature("file_attachments")

        result = await dep_func(tenant=tenant)
        assert result.id == tenant.id

    async def test_require_feature_fails(self):
        """Test feature requirement fails when feature not available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        dep_func = require_feature("file_attachments")

        with pytest.raises(HTTPException) as exc_info:
            await dep_func(tenant=tenant)

        assert exc_info.value.status_code == 403
        assert "file_attachments" in exc_info.value.detail


@pytest.mark.asyncio
class TestRequireAgent:
    """Test suite for agent requirement decorator."""

    async def test_require_agent_passes(self):
        """Test agent requirement passes when agent available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Business User {id(self)}",
            tier=TierType.BUSINESS,
        )

        dep_func = require_agent("cicd")

        result = await dep_func(tenant=tenant)
        assert result.id == tenant.id

    async def test_require_agent_fails(self):
        """Test agent requirement fails when agent not available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        dep_func = require_agent("cicd")

        with pytest.raises(HTTPException) as exc_info:
            await dep_func(tenant=tenant)

        assert exc_info.value.status_code == 403
        assert "cicd" in exc_info.value.detail.lower()


@pytest.mark.asyncio
class TestFeatureGate:
    """Test suite for feature gate class."""

    async def test_check_feature_with_access(self):
        """Test feature check returns True when feature available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Standard User",
            tier=TierType.STANDARD,
        )

        result = FeatureGate.check_feature(
            tenant=tenant,
            feature="code_generation",
            raise_error=False,
        )

        assert result is True

    async def test_check_feature_without_access(self):
        """Test feature check returns False when feature not available."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        result = FeatureGate.check_feature(
            tenant=tenant,
            feature="code_generation",
            raise_error=False,
        )

        assert result is False

    async def test_check_feature_raises_on_no_access(self):
        """Test feature check raises error when requested."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        with pytest.raises(HTTPException) as exc_info:
            FeatureGate.check_feature(
                tenant=tenant,
                feature="monitoring",
                raise_error=True,
            )

        assert exc_info.value.status_code == 403

    async def test_check_tier_passes(self):
        """Test tier check passes for sufficient tier."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Business User {id(self)}",
            tier=TierType.BUSINESS,
        )

        result = FeatureGate.check_tier(
            tenant=tenant,
            required_tier=TierType.STANDARD,
            raise_error=False,
        )

        assert result is True

    async def test_check_tier_fails(self):
        """Test tier check fails for insufficient tier."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        result = FeatureGate.check_tier(
            tenant=tenant,
            required_tier=TierType.BUSINESS,
            raise_error=False,
        )

        assert result is False

    async def test_check_tier_raises_on_failure(self):
        """Test tier check raises error when requested."""
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Free User {id(self)}",
            tier=TierType.FREE,
        )

        with pytest.raises(HTTPException) as exc_info:
            FeatureGate.check_tier(
                tenant=tenant,
                required_tier=TierType.BUSINESS,
                raise_error=True,
            )

        assert exc_info.value.status_code == 403
        assert "business" in exc_info.value.detail.lower()
