"""
Tier-based authentication and authorization middleware.

This module provides tier-based access control, feature gates, and
authentication middleware for API endpoints following 2025 best practices.
"""

from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.core.tenant import (
    Tenant,
    TenantService,
    TierType,
    get_tenant_service,
)

logger = get_logger(__name__)


class TenantContext(BaseModel):
    """Context information about the authenticated tenant."""

    tenant: Tenant
    is_authenticated: bool = True


class TierAuthMiddleware:
    """Middleware for tier-based authentication and authorization."""

    def __init__(self, tenant_service: Optional[TenantService] = None):
        """
        Initialize tier auth middleware.

        Args:
            tenant_service: Tenant service instance (uses singleton if None)
        """
        self.tenant_service = tenant_service or get_tenant_service()

    async def get_tenant_from_request(self, request: Request) -> Optional[Tenant]:
        """
        Extract and validate tenant from request.

        Looks for tenant_id in:
        1. Request headers (X-Tenant-ID)
        2. Query parameters (tenant_id)
        3. Request body (if JSON)

        Args:
            request: FastAPI request object

        Returns:
            Tenant if found and valid, None otherwise
        """
        tenant_id = None

        # Try header first
        tenant_id = request.headers.get("X-Tenant-ID")

        # Try query params
        if not tenant_id:
            tenant_id = request.query_params.get("tenant_id")

        # Try body (for POST/PUT requests)
        if not tenant_id and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                tenant_id = body.get("tenant_id")
            except Exception:
                pass

        if not tenant_id:
            return None

        # Fetch tenant from service
        tenant = await self.tenant_service.get_tenant(tenant_id)
        return tenant

    async def __call__(self, request: Request) -> TenantContext:
        """
        Process request and return tenant context.

        Args:
            request: FastAPI request object

        Returns:
            TenantContext with authenticated tenant

        Raises:
            HTTPException: If tenant not found or inactive
        """
        tenant = await self.get_tenant_from_request(request)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant ID required. Provide via X-Tenant-ID header or tenant_id parameter",
            )

        # Check tenant status
        if tenant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant account is {tenant.status}",
            )

        return TenantContext(tenant=tenant)


# Singleton middleware instance
_tier_auth_middleware = TierAuthMiddleware()


async def get_current_tenant(request: Request) -> Tenant:
    """
    Dependency to get current authenticated tenant.

    Args:
        request: FastAPI request

    Returns:
        Authenticated tenant

    Usage:
        @router.get("/resource")
        async def get_resource(tenant: Tenant = Depends(get_current_tenant)):
            ...
    """
    context = await _tier_auth_middleware(request)
    return context.tenant


def require_tier(
    *allowed_tiers: TierType,
) -> Callable:
    """
    Decorator to require specific tier(s) for an endpoint.

    Args:
        allowed_tiers: One or more tier types that are allowed

    Returns:
        Dependency function

    Usage:
        @router.post("/advanced")
        async def advanced_feature(
            tenant: Tenant = Depends(require_tier(TierType.BUSINESS))
        ):
            ...
    """

    async def tier_dependency(tenant: Tenant = Depends(get_current_tenant)) -> Tenant:
        if tenant.tier not in allowed_tiers:
            allowed_names = [t.value for t in allowed_tiers]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {' or '.join(allowed_names)} tier. "
                f"Current tier: {tenant.tier.value}",
            )
        return tenant

    return tier_dependency


def require_feature(feature_name: str) -> Callable:
    """
    Decorator to require a specific feature for an endpoint.

    Args:
        feature_name: Name of the required feature

    Returns:
        Dependency function

    Usage:
        @router.post("/code-gen")
        async def generate_code(
            tenant: Tenant = Depends(require_feature("code_generation"))
        ):
            ...
    """

    async def feature_dependency(
        tenant: Tenant = Depends(get_current_tenant),
    ) -> Tenant:
        if not tenant.has_feature(feature_name):
            tier_features = tenant.get_tier_features()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' not available in {tenant.tier.value} tier. "
                f"Upgrade to access this feature.",
            )
        return tenant

    return feature_dependency


def require_agent(agent_type: str) -> Callable:
    """
    Decorator to require access to a specific agent type.

    Args:
        agent_type: Type of agent required

    Returns:
        Dependency function

    Usage:
        @router.post("/cicd")
        async def run_cicd(
            tenant: Tenant = Depends(require_agent("cicd"))
        ):
            ...
    """

    async def agent_dependency(tenant: Tenant = Depends(get_current_tenant)) -> Tenant:
        if not tenant.can_use_agent(agent_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent '{agent_type}' not available in {tenant.tier.value} tier. "
                f"Upgrade to access this agent.",
            )
        return tenant

    return agent_dependency


# Convenience dependencies for common tiers
require_standard_or_higher = require_tier(TierType.STANDARD, TierType.BUSINESS)
require_business = require_tier(TierType.BUSINESS)


class FeatureGate:
    """
    Decorator class for feature gating at function level.

    This allows programmatic feature checks with custom logic.
    """

    @staticmethod
    def check_feature(
        tenant: Tenant,
        feature: str,
        raise_error: bool = True,
    ) -> bool:
        """
        Check if tenant has access to a feature.

        Args:
            tenant: Tenant to check
            feature: Feature name
            raise_error: Whether to raise HTTPException if check fails

        Returns:
            True if tenant has feature access

        Raises:
            HTTPException: If raise_error=True and feature not available
        """
        has_access = tenant.has_feature(feature)

        if not has_access and raise_error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' requires {TierType.STANDARD.value} or higher tier",
            )

        return has_access

    @staticmethod
    def check_tier(
        tenant: Tenant,
        required_tier: TierType,
        raise_error: bool = True,
    ) -> bool:
        """
        Check if tenant meets minimum tier requirement.

        Args:
            tenant: Tenant to check
            required_tier: Minimum required tier
            raise_error: Whether to raise HTTPException if check fails

        Returns:
            True if tenant meets requirement

        Raises:
            HTTPException: If raise_error=True and tier insufficient
        """
        # Define tier hierarchy
        tier_order = {
            TierType.FREE: 0,
            TierType.STANDARD: 1,
            TierType.BUSINESS: 2,
        }

        has_access = tier_order.get(tenant.tier, 0) >= tier_order.get(required_tier, 0)

        if not has_access and raise_error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation requires {required_tier.value} tier or higher. "
                f"Current tier: {tenant.tier.value}",
            )

        return has_access

    @staticmethod
    def check_quota(
        tenant: Tenant,
        tenant_service: TenantService,
        raise_error: bool = True,
    ) -> bool:
        """
        Check if tenant has remaining quota.

        Args:
            tenant: Tenant to check
            tenant_service: Tenant service for quota lookup
            raise_error: Whether to raise HTTPException if over quota

        Returns:
            True if quota available

        Raises:
            HTTPException: If raise_error=True and over quota
        """
        import asyncio

        # Run async check in sync context
        loop = asyncio.get_event_loop()
        usage = loop.run_until_complete(tenant_service.get_usage_today(tenant.id))

        limits = tenant.get_limits()
        over_quota = usage.is_over_quota(limits)

        if over_quota and raise_error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily quota exceeded. Limit: {limits.requests_per_day} requests/day",
            )

        return not over_quota


def feature_gate(
    features: Optional[List[str]] = None,
    min_tier: Optional[TierType] = None,
    check_quota: bool = False,
):
    """
    Function decorator for feature gating with flexible checks.

    Args:
        features: List of required features
        min_tier: Minimum required tier
        check_quota: Whether to check quota

    Usage:
        @feature_gate(features=["code_generation"], min_tier=TierType.STANDARD)
        async def my_function(tenant: Tenant, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract tenant from args/kwargs
            tenant = kwargs.get("tenant")
            if not tenant:
                for arg in args:
                    if isinstance(arg, Tenant):
                        tenant = arg
                        break

            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Feature gate requires Tenant argument",
                )

            # Check tier
            if min_tier:
                FeatureGate.check_tier(tenant, min_tier)

            # Check features
            if features:
                for feature in features:
                    FeatureGate.check_feature(tenant, feature)

            # Check quota
            if check_quota:
                tenant_service = get_tenant_service()
                FeatureGate.check_quota(tenant, tenant_service)

            # Execute function
            return await func(*args, **kwargs)

        return wrapper

    return decorator
