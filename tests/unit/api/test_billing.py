"""Tests for billing and payment integration."""

import pytest
from fastapi import HTTPException

from agentic_workflow.api.billing import (
    BillingService,
    BillingCycle,
    PaymentMethod,
    PaymentStatus,
    TIER_PRICING,
    TierUpgradeRequest,
)
from agentic_workflow.core.tenant import (
    TenantService,
    TierType,
    get_tenant_service,
)


@pytest.mark.asyncio
class TestBillingService:
    """Test suite for billing service."""

    async def test_get_tier_pricing(self):
        """Test getting pricing for all tiers."""
        billing_service = BillingService()

        # Check FREE tier
        free_pricing = billing_service.get_tier_pricing(TierType.FREE)
        assert free_pricing.monthly_price == 0.0
        assert free_pricing.tier == TierType.FREE

        # Check STANDARD tier
        standard_pricing = billing_service.get_tier_pricing(TierType.STANDARD)
        assert standard_pricing.monthly_price == 49.99
        assert standard_pricing.annual_price == 499.99

        # Check BUSINESS tier
        business_pricing = billing_service.get_tier_pricing(TierType.BUSINESS)
        assert business_pricing.monthly_price == 199.99

    async def test_calculate_price_monthly(self):
        """Test calculating monthly price."""
        billing_service = BillingService()

        price = billing_service.calculate_price(
            TierType.STANDARD,
            BillingCycle.MONTHLY,
        )

        assert price == 49.99

    async def test_calculate_price_annual(self):
        """Test calculating annual price (with discount)."""
        billing_service = BillingService()

        price = billing_service.calculate_price(
            TierType.STANDARD,
            BillingCycle.ANNUAL,
        )

        assert price == 499.99
        # Verify discount (should be less than 12 * monthly)
        assert price < (49.99 * 12)

    async def test_create_subscription(self):
        """Test creating a subscription."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.FREE,
        )

        subscription = await billing_service.create_subscription(
            tenant_id=tenant.id,
            tier=TierType.STANDARD,
            billing_cycle=BillingCycle.MONTHLY,
        )

        assert subscription.tenant_id == tenant.id
        assert subscription.tier == TierType.STANDARD
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.status == "active"
        assert subscription.auto_renew is True

    async def test_get_tenant_subscription(self):
        """Test getting tenant's active subscription."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.FREE,
        )

        # Create subscription
        subscription = await billing_service.create_subscription(
            tenant_id=tenant.id,
            tier=TierType.STANDARD,
            billing_cycle=BillingCycle.MONTHLY,
        )

        # Retrieve it
        retrieved = await billing_service.get_tenant_subscription(tenant.id)

        assert retrieved is not None
        assert retrieved.id == subscription.id
        assert retrieved.tenant_id == tenant.id

    async def test_process_payment(self):
        """Test processing a payment."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Payment Test",
            tier=TierType.FREE,
        )

        payment = await billing_service.process_payment(
            tenant_id=tenant.id,
            amount=49.99,
            payment_method=PaymentMethod.CREDIT_CARD,
            description="Monthly subscription",
        )

        assert payment.tenant_id == tenant.id
        assert payment.amount == 49.99
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.completed_at is not None

    async def test_upgrade_tier_free_to_standard(self):
        """Test upgrading from FREE to STANDARD tier."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Upgrade Test",
            tier=TierType.FREE,
        )

        response = await billing_service.upgrade_tier(
            tenant=tenant,
            target_tier=TierType.STANDARD,
            billing_cycle=BillingCycle.MONTHLY,
            payment_method=PaymentMethod.CREDIT_CARD,
            tenant_service=tenant_service,
        )

        assert response.success is True
        assert response.subscription.tier == TierType.STANDARD
        assert response.payment is not None
        assert response.payment.amount == 49.99

        # Verify tenant tier was updated
        updated_tenant = await tenant_service.get_tenant(tenant.id)
        assert updated_tenant.tier == TierType.STANDARD

    async def test_upgrade_tier_standard_to_business(self):
        """Test upgrading from STANDARD to BUSINESS tier."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Business Upgrade",
            tier=TierType.STANDARD,
        )

        response = await billing_service.upgrade_tier(
            tenant=tenant,
            target_tier=TierType.BUSINESS,
            billing_cycle=BillingCycle.ANNUAL,
            payment_method=PaymentMethod.STRIPE,
            tenant_service=tenant_service,
        )

        assert response.success is True
        assert response.subscription.tier == TierType.BUSINESS
        assert response.subscription.billing_cycle == BillingCycle.ANNUAL
        assert response.payment.amount == 1999.99

    async def test_upgrade_requires_payment_for_paid_tiers(self):
        """Test that upgrading to paid tier requires payment method."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="No Payment",
            tier=TierType.FREE,
        )

        with pytest.raises(HTTPException) as exc_info:
            await billing_service.upgrade_tier(
                tenant=tenant,
                target_tier=TierType.STANDARD,
                billing_cycle=BillingCycle.MONTHLY,
                payment_method=None,
                tenant_service=tenant_service,
            )

        assert exc_info.value.status_code == 400
        assert "payment method required" in exc_info.value.detail.lower()

    async def test_upgrade_same_tier_fails(self):
        """Test that upgrading to same tier fails."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Same Tier",
            tier=TierType.STANDARD,
        )

        with pytest.raises(HTTPException) as exc_info:
            await billing_service.upgrade_tier(
                tenant=tenant,
                target_tier=TierType.STANDARD,
                billing_cycle=BillingCycle.MONTHLY,
                payment_method=PaymentMethod.CREDIT_CARD,
                tenant_service=tenant_service,
            )

        assert exc_info.value.status_code == 400
        assert "already on" in exc_info.value.detail.lower()

    async def test_downgrade_to_free(self):
        """Test downgrading to FREE tier."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Downgrade Test",
            tier=TierType.STANDARD,
        )

        response = await billing_service.upgrade_tier(
            tenant=tenant,
            target_tier=TierType.FREE,
            billing_cycle=BillingCycle.MONTHLY,
            payment_method=None,  # No payment needed for free
            tenant_service=tenant_service,
        )

        assert response.success is True
        assert response.subscription.tier == TierType.FREE
        assert response.payment is None  # No payment for free tier

    async def test_multiple_payments_tracking(self):
        """Test tracking multiple payments."""
        billing_service = BillingService()
        tenant_service = get_tenant_service()

        tenant = await tenant_service.create_tenant(
            name="Multi Payment",
            tier=TierType.FREE,
        )

        # Process multiple payments
        payment1 = await billing_service.process_payment(
            tenant_id=tenant.id,
            amount=49.99,
            payment_method=PaymentMethod.CREDIT_CARD,
            description="Month 1",
        )

        payment2 = await billing_service.process_payment(
            tenant_id=tenant.id,
            amount=49.99,
            payment_method=PaymentMethod.CREDIT_CARD,
            description="Month 2",
        )

        # Verify both are stored
        assert payment1.id in billing_service.payments
        assert payment2.id in billing_service.payments
        assert payment1.id != payment2.id


@pytest.mark.asyncio
class TestTierPricing:
    """Test suite for tier pricing configuration."""

    def test_all_tiers_have_pricing(self):
        """Test that all tiers have pricing configuration."""
        for tier in [TierType.FREE, TierType.STANDARD, TierType.BUSINESS]:
            assert tier in TIER_PRICING
            pricing = TIER_PRICING[tier]
            assert pricing.tier == tier
            assert pricing.currency == "USD"

    def test_annual_pricing_has_discount(self):
        """Test that annual pricing includes discount."""
        for tier in [TierType.STANDARD, TierType.BUSINESS]:
            pricing = TIER_PRICING[tier]
            annual = pricing.annual_price
            monthly_total = pricing.monthly_price * 12

            # Annual should be less than 12 months (discount)
            if pricing.monthly_price > 0:
                assert annual < monthly_total

    def test_quarterly_pricing_has_discount(self):
        """Test that quarterly pricing includes discount."""
        for tier in [TierType.STANDARD, TierType.BUSINESS]:
            pricing = TIER_PRICING[tier]
            quarterly = pricing.quarterly_price
            monthly_total = pricing.monthly_price * 3

            # Quarterly should be less than 3 months (discount)
            if pricing.monthly_price > 0:
                assert quarterly < monthly_total

    def test_free_tier_is_free(self):
        """Test that FREE tier has zero cost."""
        free_pricing = TIER_PRICING[TierType.FREE]
        assert free_pricing.monthly_price == 0.0
        assert free_pricing.annual_price == 0.0
        assert free_pricing.quarterly_price == 0.0

    def test_pricing_increases_by_tier(self):
        """Test that pricing increases with tier level."""
        free_price = TIER_PRICING[TierType.FREE].monthly_price
        standard_price = TIER_PRICING[TierType.STANDARD].monthly_price
        business_price = TIER_PRICING[TierType.BUSINESS].monthly_price

        assert free_price < standard_price < business_price


@pytest.mark.asyncio
class TestTierUpgradeRequest:
    """Test suite for tier upgrade request validation."""

    def test_valid_upgrade_request(self):
        """Test creating valid upgrade request."""
        request = TierUpgradeRequest(
            target_tier=TierType.STANDARD,
            billing_cycle=BillingCycle.MONTHLY,
            payment_method=PaymentMethod.CREDIT_CARD,
        )

        assert request.target_tier == TierType.STANDARD
        assert request.billing_cycle == BillingCycle.MONTHLY
        assert request.prorate is True

    def test_upgrade_request_defaults(self):
        """Test default values in upgrade request."""
        request = TierUpgradeRequest(
            target_tier=TierType.BUSINESS,
        )

        assert request.billing_cycle == BillingCycle.MONTHLY
        assert request.prorate is True
        assert request.payment_method is None
