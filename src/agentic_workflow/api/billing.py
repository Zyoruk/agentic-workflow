"""
Billing and payment integration API endpoints.

This module provides endpoints for managing subscriptions, payments,
and tier upgrades/downgrades following 2025 best practices.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from agentic_workflow.api.tier_auth import get_current_tenant
from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.core.tenant import (
    Tenant,
    TenantService,
    TierType,
    get_tenant_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"


class PaymentStatus(str, Enum):
    """Payment processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingCycle(str, Enum):
    """Billing cycle periods."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class TierPricing(BaseModel):
    """Pricing information for a tier."""

    tier: TierType
    monthly_price: float = Field(ge=0, description="Monthly price in USD")
    annual_price: float = Field(ge=0, description="Annual price in USD")
    quarterly_price: float = Field(ge=0, description="Quarterly price in USD")
    currency: str = Field(default="USD")
    features_summary: List[str] = Field(
        default_factory=list,
        description="Key features included",
    )


# Tier pricing configuration
TIER_PRICING: Dict[TierType, TierPricing] = {
    TierType.FREE: TierPricing(
        tier=TierType.FREE,
        monthly_price=0.0,
        annual_price=0.0,
        quarterly_price=0.0,
        features_summary=[
            "50 requests/day",
            "10K token prompts",
            "Planning agent only",
            "No file attachments",
        ],
    ),
    TierType.STANDARD: TierPricing(
        tier=TierType.STANDARD,
        monthly_price=49.99,
        annual_price=499.99,  # 2 months free
        quarterly_price=134.99,  # 10% discount
        features_summary=[
            "1,000 requests/day",
            "100K token prompts",
            "All agents except CI/CD",
            "100MB file uploads",
            "30-day data retention",
            "Preference storage",
        ],
    ),
    TierType.BUSINESS: TierPricing(
        tier=TierType.BUSINESS,
        monthly_price=199.99,
        annual_price=1999.99,  # 2 months free
        quarterly_price=539.99,  # 10% discount
        features_summary=[
            "10,000 requests/day",
            "500K token prompts",
            "All agents including CI/CD",
            "1GB file uploads",
            "365-day data retention",
            "Advanced monitoring",
            "Sentiment analysis",
            "Enterprise APIs",
            "Priority support",
            "Audit logging",
        ],
    ),
}


class PaymentMethodInfo(BaseModel):
    """Payment method information."""

    payment_method: PaymentMethod
    card_last4: Optional[str] = Field(default=None, min_length=4, max_length=4)
    card_brand: Optional[str] = None
    expiry_month: Optional[int] = Field(default=None, ge=1, le=12)
    expiry_year: Optional[int] = Field(default=None, ge=2024)
    is_default: bool = Field(default=False)


class Subscription(BaseModel):
    """Subscription model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    tier: TierType
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY)
    status: str = Field(default="active")
    current_period_start: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    current_period_end: datetime
    auto_renew: bool = Field(default=True)
    payment_method: Optional[PaymentMethodInfo] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Payment(BaseModel):
    """Payment transaction record."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    subscription_id: Optional[str] = None
    amount: float = Field(ge=0)
    currency: str = Field(default="USD")
    status: PaymentStatus
    payment_method: PaymentMethod
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TierUpgradeRequest(BaseModel):
    """Request to upgrade/change subscription tier."""

    target_tier: TierType = Field(..., description="Target tier to upgrade/downgrade to")
    billing_cycle: BillingCycle = Field(
        default=BillingCycle.MONTHLY,
        description="Billing cycle for new tier",
    )
    payment_method: Optional[PaymentMethod] = Field(
        default=None,
        description="Payment method (required for paid tiers)",
    )
    prorate: bool = Field(
        default=True,
        description="Whether to prorate the charge",
    )

    @field_validator("target_tier")
    @classmethod
    def validate_tier(cls, v: TierType) -> TierType:
        """Validate target tier."""
        if v not in [TierType.FREE, TierType.STANDARD, TierType.BUSINESS]:
            raise ValueError(f"Invalid tier: {v}")
        return v


class TierUpgradeResponse(BaseModel):
    """Response for tier upgrade request."""

    success: bool
    subscription: Subscription
    payment: Optional[Payment] = None
    proration_amount: float = Field(default=0.0)
    message: str


class BillingService:
    """Service for billing and payment operations (MVP with in-memory storage)."""

    def __init__(self):
        """Initialize billing service."""
        self.subscriptions: Dict[str, Subscription] = {}
        self.payments: Dict[str, Payment] = {}

    def get_tier_pricing(self, tier: TierType) -> TierPricing:
        """Get pricing for a tier."""
        return TIER_PRICING[tier]

    def calculate_price(self, tier: TierType, billing_cycle: BillingCycle) -> float:
        """Calculate price for tier and billing cycle."""
        pricing = self.get_tier_pricing(tier)

        if billing_cycle == BillingCycle.MONTHLY:
            return pricing.monthly_price
        elif billing_cycle == BillingCycle.QUARTERLY:
            return pricing.quarterly_price
        elif billing_cycle == BillingCycle.ANNUAL:
            return pricing.annual_price

        return pricing.monthly_price

    async def create_subscription(
        self,
        tenant_id: str,
        tier: TierType,
        billing_cycle: BillingCycle,
        payment_method: Optional[PaymentMethodInfo] = None,
    ) -> Subscription:
        """Create a new subscription."""
        from datetime import timedelta

        # Calculate period end based on billing cycle
        now = datetime.now(timezone.utc)
        if billing_cycle == BillingCycle.MONTHLY:
            period_end = now + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            period_end = now + timedelta(days=90)
        else:  # ANNUAL
            period_end = now + timedelta(days=365)

        subscription = Subscription(
            tenant_id=tenant_id,
            tier=tier,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
            payment_method=payment_method,
        )

        self.subscriptions[subscription.id] = subscription
        return subscription

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self.subscriptions.get(subscription_id)

    async def get_tenant_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get active subscription for a tenant."""
        for sub in self.subscriptions.values():
            if sub.tenant_id == tenant_id and sub.status == "active":
                return sub
        return None

    async def process_payment(
        self,
        tenant_id: str,
        amount: float,
        payment_method: PaymentMethod,
        description: str,
        subscription_id: Optional[str] = None,
    ) -> Payment:
        """Process a payment (mock implementation)."""
        payment = Payment(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            amount=amount,
            status=PaymentStatus.PROCESSING,
            payment_method=payment_method,
            description=description,
        )

        # Mock payment processing
        logger.info(
            f"Processing payment: {payment.id} for tenant {tenant_id}, "
            f"amount: ${amount:.2f}"
        )

        # Simulate successful payment
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.now(timezone.utc)

        self.payments[payment.id] = payment
        return payment

    async def upgrade_tier(
        self,
        tenant: Tenant,
        target_tier: TierType,
        billing_cycle: BillingCycle,
        payment_method: Optional[PaymentMethod],
        tenant_service: TenantService,
    ) -> TierUpgradeResponse:
        """Upgrade tenant to a new tier."""
        current_tier = tenant.tier

        # Validate upgrade path
        if current_tier == target_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already on {target_tier.value} tier",
            )

        # Check if payment method required
        price = self.calculate_price(target_tier, billing_cycle)
        if price > 0 and not payment_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment method required for paid tiers",
            )

        # Process payment if needed
        payment = None
        if price > 0:
            payment = await self.process_payment(
                tenant_id=tenant.id,
                amount=price,
                payment_method=payment_method,
                description=f"Upgrade to {target_tier.value} tier ({billing_cycle.value})",
            )

        # Create/update subscription
        subscription = await self.create_subscription(
            tenant_id=tenant.id,
            tier=target_tier,
            billing_cycle=billing_cycle,
        )

        # Update tenant tier
        await tenant_service.update_tenant(
            tenant_id=tenant.id,
            tier=target_tier,
        )

        logger.info(
            f"Upgraded tenant {tenant.id} from {current_tier.value} "
            f"to {target_tier.value}"
        )

        return TierUpgradeResponse(
            success=True,
            subscription=subscription,
            payment=payment,
            proration_amount=0.0,  # TODO: Implement proration logic
            message=f"Successfully upgraded to {target_tier.value} tier",
        )


# Singleton service instance
_billing_service = BillingService()


def get_billing_service() -> BillingService:
    """Get billing service singleton."""
    return _billing_service


# API Endpoints


@router.get("/pricing", response_model=List[TierPricing])
async def get_pricing():
    """
    Get pricing information for all tiers.

    Returns:
        List of tier pricing information
    """
    return list(TIER_PRICING.values())


@router.get("/pricing/{tier}", response_model=TierPricing)
async def get_tier_pricing(tier: TierType):
    """
    Get pricing for a specific tier.

    Args:
        tier: Tier type

    Returns:
        Pricing information for the tier
    """
    return TIER_PRICING[tier]


@router.post("/subscribe", response_model=Subscription)
async def create_subscription(
    tier: TierType,
    billing_cycle: BillingCycle = BillingCycle.MONTHLY,
    payment_method: Optional[PaymentMethod] = None,
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
):
    """
    Create a new subscription for the tenant.

    Args:
        tier: Subscription tier
        billing_cycle: Billing cycle
        payment_method: Payment method (required for paid tiers)
        tenant: Current tenant
        billing_service: Billing service

    Returns:
        Created subscription
    """
    # Check if payment method required
    price = billing_service.calculate_price(tier, billing_cycle)
    if price > 0 and not payment_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method required for paid tiers",
        )

    # Check for existing subscription
    existing = await billing_service.get_tenant_subscription(tenant.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant already has an active subscription. Use upgrade endpoint.",
        )

    subscription = await billing_service.create_subscription(
        tenant_id=tenant.id,
        tier=tier,
        billing_cycle=billing_cycle,
    )

    return subscription


@router.get("/subscription", response_model=Optional[Subscription])
async def get_current_subscription(
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
):
    """
    Get current subscription for the authenticated tenant.

    Args:
        tenant: Current tenant
        billing_service: Billing service

    Returns:
        Current subscription or None
    """
    return await billing_service.get_tenant_subscription(tenant.id)


@router.post("/upgrade", response_model=TierUpgradeResponse)
async def upgrade_subscription(
    request: TierUpgradeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
    tenant_service: TenantService = Depends(get_tenant_service),
):
    """
    Upgrade or downgrade subscription tier.

    Args:
        request: Tier upgrade request
        tenant: Current tenant
        billing_service: Billing service
        tenant_service: Tenant service

    Returns:
        Upgrade response with subscription and payment details
    """
    return await billing_service.upgrade_tier(
        tenant=tenant,
        target_tier=request.target_tier,
        billing_cycle=request.billing_cycle,
        payment_method=request.payment_method,
        tenant_service=tenant_service,
    )


@router.post("/downgrade", response_model=TierUpgradeResponse)
async def downgrade_subscription(
    target_tier: TierType,
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
    tenant_service: TenantService = Depends(get_tenant_service),
):
    """
    Downgrade to a lower tier (takes effect at end of billing period).

    Args:
        target_tier: Target tier to downgrade to
        tenant: Current tenant
        billing_service: Billing service
        tenant_service: Tenant service

    Returns:
        Downgrade confirmation
    """
    current_tier = tenant.tier

    # Define tier hierarchy for validation
    tier_order = {
        TierType.FREE: 0,
        TierType.STANDARD: 1,
        TierType.BUSINESS: 2,
    }

    if tier_order.get(target_tier, 0) >= tier_order.get(current_tier, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use upgrade endpoint for tier upgrades",
        )

    # For downgrades, no immediate payment needed
    return await billing_service.upgrade_tier(
        tenant=tenant,
        target_tier=target_tier,
        billing_cycle=BillingCycle.MONTHLY,
        payment_method=None,
        tenant_service=tenant_service,
    )


@router.get("/payments", response_model=List[Payment])
async def list_payments(
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
):
    """
    List all payments for the authenticated tenant.

    Args:
        tenant: Current tenant
        billing_service: Billing service

    Returns:
        List of payments
    """
    payments = [
        payment
        for payment in billing_service.payments.values()
        if payment.tenant_id == tenant.id
    ]
    return sorted(payments, key=lambda p: p.created_at, reverse=True)


@router.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    billing_service: BillingService = Depends(get_billing_service),
):
    """
    Get details of a specific payment.

    Args:
        payment_id: Payment ID
        tenant: Current tenant
        billing_service: Billing service

    Returns:
        Payment details
    """
    payment = billing_service.payments.get(payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    # Ensure tenant owns this payment
    if payment.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return payment


@router.get("/usage-cost", response_model=Dict[str, Any])
async def get_usage_cost_estimate(
    tenant: Tenant = Depends(get_current_tenant),
    tenant_service: TenantService = Depends(get_tenant_service),
):
    """
    Get usage and cost estimate for current billing period.

    Args:
        tenant: Current tenant
        tenant_service: Tenant service

    Returns:
        Usage statistics and cost estimate
    """
    usage = await tenant_service.get_usage_today(tenant.id)
    limits = tenant.get_limits()
    pricing = TIER_PRICING[tenant.tier]

    return {
        "tenant_id": tenant.id,
        "current_tier": tenant.tier.value,
        "usage": {
            "requests": {
                "used": usage.requests_count,
                "limit": limits.requests_per_day,
                "percentage": (
                    usage.requests_count / limits.requests_per_day * 100
                    if limits.requests_per_day > 0
                    else 0
                ),
            },
            "tokens": usage.tokens_used,
            "files": usage.files_uploaded,
            "storage_mb": usage.storage_bytes / (1024 * 1024),
        },
        "current_cost": {
            "monthly": pricing.monthly_price,
            "quarterly": pricing.quarterly_price,
            "annual": pricing.annual_price,
            "currency": pricing.currency,
        },
    }
