"""
Tenant management system for multi-tenancy support.

This module provides tenant isolation, preference management, and
tier-based access control following 2025 best practices.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .logging_config import get_logger

logger = get_logger(__name__)


class TierType(str, Enum):
    """Subscription tier types."""

    FREE = "free"
    STANDARD = "standard"
    BUSINESS = "business"


class TenantStatus(str, Enum):
    """Tenant account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class TierLimits(BaseModel):
    """Resource limits for a subscription tier."""

    max_prompt_size: int = Field(
        description="Maximum prompt size in tokens"
    )
    requests_per_day: int = Field(
        description="Maximum API requests per day"
    )
    storage_days: int = Field(
        description="Number of days to retain data (0 = no retention)"
    )
    max_file_size_mb: int = Field(
        default=0,
        description="Maximum file upload size in MB"
    )
    file_attachments: bool = Field(
        default=False,
        description="Whether file attachments are enabled"
    )
    preference_storage: bool = Field(
        default=False,
        description="Whether preference storage is enabled"
    )
    audit_logging: bool = Field(
        default=False,
        description="Whether audit logging is enabled"
    )


class TierFeatures(BaseModel):
    """Features available for a subscription tier."""

    name: TierType
    features: List[str] = Field(
        description="List of enabled feature names"
    )
    limits: TierLimits
    agents: List[str] = Field(
        description="List of allowed agent types"
    )


# Tier configurations following 2025 best practices
TIER_CONFIGURATIONS: Dict[TierType, TierFeatures] = {
    TierType.FREE: TierFeatures(
        name=TierType.FREE,
        features=[
            "prompt_processing",
            "planning",
            "analysis",
        ],
        limits=TierLimits(
            max_prompt_size=10000,
            requests_per_day=50,
            storage_days=0,
            max_file_size_mb=0,
            file_attachments=False,
            preference_storage=False,
            audit_logging=False,
        ),
        agents=["planning"],
    ),
    TierType.STANDARD: TierFeatures(
        name=TierType.STANDARD,
        features=[
            "prompt_processing",
            "planning",
            "analysis",
            "code_generation",
            "testing",
            "review",
            "file_attachments",
            "preference_storage",
        ],
        limits=TierLimits(
            max_prompt_size=100000,
            requests_per_day=1000,
            storage_days=30,
            max_file_size_mb=100,
            file_attachments=True,
            preference_storage=True,
            audit_logging=False,
        ),
        agents=[
            "planning",
            "code_generation",
            "testing",
            "review",
            "requirement_engineering",
        ],
    ),
    TierType.BUSINESS: TierFeatures(
        name=TierType.BUSINESS,
        features=[
            "prompt_processing",
            "planning",
            "analysis",
            "code_generation",
            "testing",
            "review",
            "file_attachments",
            "preference_storage",
            "monitoring",
            "metrics",
            "sentiment_analysis",
            "cicd_integration",
            "enterprise_apis",
            "custom_agents",
            "priority_support",
            "audit_logging",
        ],
        limits=TierLimits(
            max_prompt_size=500000,
            requests_per_day=10000,
            storage_days=365,
            max_file_size_mb=1000,
            file_attachments=True,
            preference_storage=True,
            audit_logging=True,
        ),
        agents=[
            "planning",
            "code_generation",
            "testing",
            "review",
            "requirement_engineering",
            "cicd",
            "program_manager",
        ],
    ),
}


class Tenant(BaseModel):
    """Tenant model representing a customer account."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    tier: TierType = Field(default=TierType.FREE)
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tenant name."""
        if not v or not v.strip():
            raise ValueError("Tenant name cannot be empty")
        return v.strip()

    def get_tier_features(self) -> TierFeatures:
        """Get features for this tenant's tier."""
        return TIER_CONFIGURATIONS[self.tier]

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has access to a feature."""
        tier_features = self.get_tier_features()
        return feature in tier_features.features

    def can_use_agent(self, agent_type: str) -> bool:
        """Check if tenant can use a specific agent type."""
        tier_features = self.get_tier_features()
        return agent_type in tier_features.agents or "all" in tier_features.agents

    def get_limits(self) -> TierLimits:
        """Get resource limits for this tenant."""
        return self.get_tier_features().limits


class TenantPreference(BaseModel):
    """Tenant preference for customization."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant this preference belongs to")
    preference_key: str = Field(..., min_length=1, max_length=255)
    preference_value: Dict[str, Any] = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("preference_key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate preference key."""
        if not v or not v.strip():
            raise ValueError("Preference key cannot be empty")
        return v.strip()


class TenantUsage(BaseModel):
    """Daily usage tracking for a tenant."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    requests_count: int = Field(default=0, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    files_uploaded: int = Field(default=0, ge=0)
    storage_bytes: int = Field(default=0, ge=0)

    def is_over_quota(self, tier_limits: TierLimits) -> bool:
        """Check if usage exceeds tier limits."""
        return self.requests_count >= tier_limits.requests_per_day

    def get_quota_status(self, tier_limits: TierLimits) -> Dict[str, Any]:
        """Get quota status information."""
        return {
            "requests": {
                "used": self.requests_count,
                "limit": tier_limits.requests_per_day,
                "percentage": (
                    self.requests_count / tier_limits.requests_per_day * 100
                    if tier_limits.requests_per_day > 0
                    else 0
                ),
            },
            "tokens": {
                "used": self.tokens_used,
            },
            "storage": {
                "used_bytes": self.storage_bytes,
                "used_mb": self.storage_bytes / (1024 * 1024),
            },
            "files": {
                "uploaded": self.files_uploaded,
            },
        }


class TenantService:
    """Service for tenant management operations."""

    def __init__(self) -> None:
        """Initialize tenant service."""
        # In-memory storage for MVP (replace with database in production)
        self._tenants: Dict[str, Tenant] = {}
        self._preferences: Dict[str, Dict[str, TenantPreference]] = {}
        self._usage: Dict[str, TenantUsage] = {}
        logger.info("TenantService initialized")

    async def create_tenant(
        self,
        name: str,
        tier: TierType = TierType.FREE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """Create a new tenant.

        Args:
            name: Tenant name
            tier: Subscription tier
            metadata: Additional tenant metadata

        Returns:
            Created tenant

        Raises:
            ValueError: If tenant with same name exists
        """
        # Check for duplicate name
        for tenant in self._tenants.values():
            if tenant.name.lower() == name.lower():
                raise ValueError(f"Tenant with name '{name}' already exists")

        tenant = Tenant(
            name=name,
            tier=tier,
            metadata=metadata or {},
        )
        self._tenants[tenant.id] = tenant
        self._preferences[tenant.id] = {}

        # Initialize usage tracking
        self._usage[tenant.id] = TenantUsage(tenant_id=tenant.id)

        logger.info(f"Created tenant: {tenant.id} ({tenant.name}) with tier {tier}")
        return tenant

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant if found, None otherwise
        """
        return self._tenants.get(tenant_id)

    async def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        tier: Optional[TierType] = None,
    ) -> List[Tenant]:
        """List tenants with optional filtering.

        Args:
            status: Filter by status
            tier: Filter by tier

        Returns:
            List of tenants matching filters
        """
        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]

        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        return tenants

    async def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        tier: Optional[TierType] = None,
        status: Optional[TenantStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tenant]:
        """Update tenant information.

        Args:
            tenant_id: Tenant UUID
            name: New name (optional)
            tier: New tier (optional)
            status: New status (optional)
            metadata: Updated metadata (optional)

        Returns:
            Updated tenant if found, None otherwise
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        if name is not None:
            tenant.name = name
        if tier is not None:
            old_tier = tenant.tier
            tenant.tier = tier
            logger.info(f"Tenant {tenant_id} tier changed: {old_tier} -> {tier}")
        if status is not None:
            tenant.status = status
        if metadata is not None:
            tenant.metadata.update(metadata)

        tenant.updated_at = datetime.now(timezone.utc)
        return tenant

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant and all associated data.

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if deleted, False if not found
        """
        if tenant_id not in self._tenants:
            return False

        # Clean up all tenant data
        del self._tenants[tenant_id]
        if tenant_id in self._preferences:
            del self._preferences[tenant_id]
        if tenant_id in self._usage:
            del self._usage[tenant_id]

        logger.info(f"Deleted tenant: {tenant_id}")
        return True

    async def set_preference(
        self,
        tenant_id: str,
        key: str,
        value: Dict[str, Any],
    ) -> Optional[TenantPreference]:
        """Set a tenant preference.

        Args:
            tenant_id: Tenant UUID
            key: Preference key
            value: Preference value

        Returns:
            Created/updated preference if tenant exists, None otherwise
        """
        if tenant_id not in self._tenants:
            return None

        # Check if tenant tier allows preferences
        tenant = self._tenants[tenant_id]
        if not tenant.get_limits().preference_storage:
            raise ValueError(
                f"Tenant tier '{tenant.tier}' does not support preference storage"
            )

        if tenant_id not in self._preferences:
            self._preferences[tenant_id] = {}

        preference = TenantPreference(
            tenant_id=tenant_id,
            preference_key=key,
            preference_value=value,
        )
        self._preferences[tenant_id][key] = preference

        logger.debug(f"Set preference for tenant {tenant_id}: {key}")
        return preference

    async def get_preference(
        self, tenant_id: str, key: str
    ) -> Optional[TenantPreference]:
        """Get a tenant preference.

        Args:
            tenant_id: Tenant UUID
            key: Preference key

        Returns:
            Preference if found, None otherwise
        """
        if tenant_id not in self._preferences:
            return None
        return self._preferences[tenant_id].get(key)

    async def get_all_preferences(
        self, tenant_id: str
    ) -> Dict[str, TenantPreference]:
        """Get all preferences for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary of preferences
        """
        return self._preferences.get(tenant_id, {})

    async def delete_preference(self, tenant_id: str, key: str) -> bool:
        """Delete a tenant preference.

        Args:
            tenant_id: Tenant UUID
            key: Preference key

        Returns:
            True if deleted, False if not found
        """
        if tenant_id not in self._preferences:
            return False
        if key not in self._preferences[tenant_id]:
            return False

        del self._preferences[tenant_id][key]
        logger.debug(f"Deleted preference for tenant {tenant_id}: {key}")
        return True

    async def track_usage(
        self,
        tenant_id: str,
        requests: int = 0,
        tokens: int = 0,
        files: int = 0,
        storage_bytes: int = 0,
    ) -> Optional[TenantUsage]:
        """Track tenant usage.

        Args:
            tenant_id: Tenant UUID
            requests: Number of requests to add
            tokens: Number of tokens to add
            files: Number of files to add
            storage_bytes: Storage bytes to add

        Returns:
            Updated usage if tenant exists, None otherwise
        """
        if tenant_id not in self._tenants:
            return None

        if tenant_id not in self._usage:
            self._usage[tenant_id] = TenantUsage(tenant_id=tenant_id)

        usage = self._usage[tenant_id]
        usage.requests_count += requests
        usage.tokens_used += tokens
        usage.files_uploaded += files
        usage.storage_bytes += storage_bytes

        return usage

    async def get_usage(self, tenant_id: str) -> Optional[TenantUsage]:
        """Get current usage for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Usage data if tenant exists, None otherwise
        """
        return self._usage.get(tenant_id)

    async def check_quota(
        self, tenant_id: str, operation: str = "request"
    ) -> Dict[str, Any]:
        """Check if operation is within tenant quota.

        Args:
            tenant_id: Tenant UUID
            operation: Operation type to check

        Returns:
            Quota check result with status and details
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {"allowed": False, "reason": "Tenant not found"}

        if tenant.status != TenantStatus.ACTIVE:
            return {"allowed": False, "reason": f"Tenant status: {tenant.status}"}

        usage = self._usage.get(tenant_id)
        if not usage:
            return {"allowed": True, "reason": "No usage data"}

        limits = tenant.get_limits()

        if operation == "request":
            if usage.is_over_quota(limits):
                return {
                    "allowed": False,
                    "reason": "Daily request quota exceeded",
                    "quota_status": usage.get_quota_status(limits),
                }

        return {
            "allowed": True,
            "quota_status": usage.get_quota_status(limits),
        }

    def get_tier_info(self, tier: TierType) -> TierFeatures:
        """Get information about a tier.

        Args:
            tier: Tier type

        Returns:
            Tier features and limits
        """
        return TIER_CONFIGURATIONS[tier]

    def list_all_tiers(self) -> List[TierFeatures]:
        """List all available tiers.

        Returns:
            List of all tier configurations
        """
        return list(TIER_CONFIGURATIONS.values())


# Global tenant service instance
_tenant_service: Optional[TenantService] = None


def get_tenant_service() -> TenantService:
    """Get or create the global tenant service instance.

    Returns:
        TenantService instance
    """
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService()
    return _tenant_service
