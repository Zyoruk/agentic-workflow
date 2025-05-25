import pytest

from agentic_workflow.guardrails.resource_limits import ResourceLimiter, ResourceType


@pytest.mark.unit
def test_set_and_increment_usage():
    limiter = ResourceLimiter()
    limiter.set_limit("test", ResourceType.API_CALLS, 2, "per_minute")
    assert limiter.increment_usage("test", ResourceType.API_CALLS, unit="per_minute")
    assert limiter.increment_usage("test", ResourceType.API_CALLS, unit="per_minute")
    # Third call should exceed limit
    assert not limiter.increment_usage(
        "test", ResourceType.API_CALLS, unit="per_minute"
    )


@pytest.mark.unit
def test_reset_usage():
    limiter = ResourceLimiter()
    limiter.set_limit("test", ResourceType.API_CALLS, 1, "per_minute")
    limiter.increment_usage("test", ResourceType.API_CALLS, unit="per_minute")
    limiter.reset_usage("test", ResourceType.API_CALLS)
    # Should allow again after reset
    assert limiter.increment_usage("test", ResourceType.API_CALLS, unit="per_minute")
