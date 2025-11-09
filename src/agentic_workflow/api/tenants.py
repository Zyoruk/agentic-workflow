"""
Tenant management API endpoints.

This module provides REST API endpoints for tenant management,
preferences, and tier operations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agentic_workflow.core.tenant import (
    TenantService,
    TenantStatus,
    TierType,
    get_tenant_service,
)
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


# Request/Response Models
class CreateTenantRequest(BaseModel):
    """Request to create a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    tier: TierType = Field(default=TierType.FREE)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tier: Optional[TierType] = None
    status: Optional[TenantStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Response model for tenant operations."""

    id: str
    name: str
    tier: TierType
    status: TenantStatus
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class SetPreferenceRequest(BaseModel):
    """Request to set a preference."""

    preference_key: str = Field(..., min_length=1)
    preference_value: Dict[str, Any]


class PreferenceResponse(BaseModel):
    """Response model for preference operations."""

    id: str
    tenant_id: str
    preference_key: str
    preference_value: Dict[str, Any]
    created_at: str
    updated_at: str


class TierInfoResponse(BaseModel):
    """Response model for tier information."""

    name: TierType
    features: List[str]
    limits: Dict[str, Any]
    agents: List[str]


class UsageResponse(BaseModel):
    """Response model for usage information."""

    tenant_id: str
    date: str
    requests_count: int
    tokens_used: int
    files_uploaded: int
    storage_bytes: int
    quota_status: Dict[str, Any]


# Endpoints

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(request: CreateTenantRequest) -> Dict[str, Any]:
    """Create a new tenant.

    Creates a tenant with the specified tier and metadata.
    """
    try:
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=request.name,
            tier=request.tier,
            metadata=request.metadata,
        )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier,
            "status": tenant.status,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
            "metadata": tenant.metadata,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant",
        )


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    tier: Optional[TierType] = None,
    tenant_status: Optional[TenantStatus] = None,
) -> List[Dict[str, Any]]:
    """List tenants with optional filtering.

    Query parameters:
    - tier: Filter by subscription tier
    - status: Filter by tenant status
    """
    try:
        tenant_service = get_tenant_service()
        tenants = await tenant_service.list_tenants(
            status=tenant_status,
            tier=tier,
        )

        return [
            {
                "id": t.id,
                "name": t.name,
                "tier": t.tier,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "metadata": t.metadata,
            }
            for t in tenants
        ]

    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tenants",
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str) -> Dict[str, Any]:
    """Get tenant details by ID."""
    try:
        tenant_service = get_tenant_service()
        tenant = await tenant_service.get_tenant(tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier,
            "status": tenant.status,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
            "metadata": tenant.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tenant",
        )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str, request: UpdateTenantRequest
) -> Dict[str, Any]:
    """Update tenant information."""
    try:
        tenant_service = get_tenant_service()
        tenant = await tenant_service.update_tenant(
            tenant_id=tenant_id,
            name=request.name,
            tier=request.tier,
            status=request.status,
            metadata=request.metadata,
        )

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        return {
            "id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier,
            "status": tenant.status,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
            "metadata": tenant.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tenant",
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: str) -> None:
    """Delete a tenant and all associated data."""
    try:
        tenant_service = get_tenant_service()
        deleted = await tenant_service.delete_tenant(tenant_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant",
        )


# Preference endpoints

@router.post(
    "/{tenant_id}/preferences",
    response_model=PreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_preference(
    tenant_id: str, request: SetPreferenceRequest
) -> Dict[str, Any]:
    """Set a tenant preference."""
    try:
        tenant_service = get_tenant_service()
        preference = await tenant_service.set_preference(
            tenant_id=tenant_id,
            key=request.preference_key,
            value=request.preference_value,
        )

        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        return {
            "id": preference.id,
            "tenant_id": preference.tenant_id,
            "preference_key": preference.preference_key,
            "preference_value": preference.preference_value,
            "created_at": preference.created_at.isoformat(),
            "updated_at": preference.updated_at.isoformat(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set preference for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set preference",
        )


@router.get("/{tenant_id}/preferences", response_model=Dict[str, PreferenceResponse])
async def get_preferences(tenant_id: str) -> Dict[str, Any]:
    """Get all preferences for a tenant."""
    try:
        tenant_service = get_tenant_service()
        preferences = await tenant_service.get_all_preferences(tenant_id)

        return {
            key: {
                "id": pref.id,
                "tenant_id": pref.tenant_id,
                "preference_key": pref.preference_key,
                "preference_value": pref.preference_value,
                "created_at": pref.created_at.isoformat(),
                "updated_at": pref.updated_at.isoformat(),
            }
            for key, pref in preferences.items()
        }

    except Exception as e:
        logger.error(f"Failed to get preferences for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences",
        )


@router.get(
    "/{tenant_id}/preferences/{preference_key}",
    response_model=PreferenceResponse,
)
async def get_preference(tenant_id: str, preference_key: str) -> Dict[str, Any]:
    """Get a specific preference for a tenant."""
    try:
        tenant_service = get_tenant_service()
        preference = await tenant_service.get_preference(tenant_id, preference_key)

        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preference not found: {preference_key}",
            )

        return {
            "id": preference.id,
            "tenant_id": preference.tenant_id,
            "preference_key": preference.preference_key,
            "preference_value": preference.preference_value,
            "created_at": preference.created_at.isoformat(),
            "updated_at": preference.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get preference {preference_key} for tenant {tenant_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preference",
        )


@router.delete(
    "/{tenant_id}/preferences/{preference_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_preference(tenant_id: str, preference_key: str) -> None:
    """Delete a tenant preference."""
    try:
        tenant_service = get_tenant_service()
        deleted = await tenant_service.delete_preference(tenant_id, preference_key)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preference not found: {preference_key}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to delete preference {preference_key} for tenant {tenant_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete preference",
        )


# Usage and tier endpoints

@router.get("/{tenant_id}/usage", response_model=UsageResponse)
async def get_usage(tenant_id: str) -> Dict[str, Any]:
    """Get current usage for a tenant."""
    try:
        tenant_service = get_tenant_service()
        
        # Get tenant for limits
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        usage = await tenant_service.get_usage(tenant_id)
        if not usage:
            # No usage yet, return zeros
            return {
                "tenant_id": tenant_id,
                "date": "",
                "requests_count": 0,
                "tokens_used": 0,
                "files_uploaded": 0,
                "storage_bytes": 0,
                "quota_status": {
                    "requests": {"used": 0, "limit": tenant.get_limits().requests_per_day},
                    "tokens": {"used": 0},
                    "storage": {"used_bytes": 0, "used_mb": 0},
                    "files": {"uploaded": 0},
                },
            }

        limits = tenant.get_limits()
        return {
            "tenant_id": usage.tenant_id,
            "date": usage.date.isoformat() if hasattr(usage.date, 'isoformat') else str(usage.date),
            "requests_count": usage.requests_count,
            "tokens_used": usage.tokens_used,
            "files_uploaded": usage.files_uploaded,
            "storage_bytes": usage.storage_bytes,
            "quota_status": usage.get_quota_status(limits),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage",
        )


@router.get("/{tenant_id}/tier", response_model=TierInfoResponse)
async def get_tenant_tier(tenant_id: str) -> Dict[str, Any]:
    """Get tier information for a tenant."""
    try:
        tenant_service = get_tenant_service()
        tenant = await tenant_service.get_tenant(tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        tier_features = tenant.get_tier_features()
        return {
            "name": tier_features.name,
            "features": tier_features.features,
            "limits": tier_features.limits.model_dump(),
            "agents": tier_features.agents,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tier for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tier",
        )


@router.get("/tiers/all", response_model=List[TierInfoResponse])
async def list_all_tiers() -> List[Dict[str, Any]]:
    """List all available subscription tiers."""
    try:
        tenant_service = get_tenant_service()
        tiers = tenant_service.list_all_tiers()

        return [
            {
                "name": tier.name,
                "features": tier.features,
                "limits": tier.limits.model_dump(),
                "agents": tier.agents,
            }
            for tier in tiers
        ]

    except Exception as e:
        logger.error(f"Failed to list tiers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tiers",
        )


@router.post("/{tenant_id}/quota-check")
async def check_quota(tenant_id: str, operation: str = "request") -> Dict[str, Any]:
    """Check if operation is within tenant quota.

    Returns whether the operation is allowed and quota status.
    """
    try:
        tenant_service = get_tenant_service()
        result = await tenant_service.check_quota(tenant_id, operation)
        return result

    except Exception as e:
        logger.error(f"Failed to check quota for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check quota",
        )
