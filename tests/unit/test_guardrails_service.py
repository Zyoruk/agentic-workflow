"""Tests for guardrails service."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_workflow.core.exceptions import ResourceLimitError, SecurityViolationError
from agentic_workflow.core.interfaces import ComponentStatus
from agentic_workflow.guardrails.error_handling import ErrorSeverity, RecoveryStrategy
from agentic_workflow.guardrails.resource_limits import ResourceType
from agentic_workflow.guardrails.safety_checks import SafetyLevel
from agentic_workflow.guardrails.service import GuardrailsService


class TestGuardrailsService:
    """Test guardrails service functionality."""

    @pytest.fixture
    def service(self):
        """Create guardrails service fixture."""
        return GuardrailsService()

    @pytest.mark.asyncio
    async def test_initialize(self, service):
        """Test service initialization."""
        await service.initialize()
        assert service.initialized
        assert service.status == ComponentStatus.READY

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """Test initialization failure."""
        with patch.object(
            service.safety_checker,
            "register_violation_handler",
            side_effect=Exception("Test error"),
        ):
            with pytest.raises(Exception):
                await service.initialize()
        assert not service.initialized
        assert service.status == ComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_process_request_validation(self, service):
        """Test request validation."""
        await service.initialize()

        # Test with invalid request
        request = {"action": "test", "parameters": None}
        response = await service.process_request(request)
        assert not response.success
        assert "validation" in response.error.lower()
        assert service.validation_failures == 1

        # Test with valid request
        request = {"action": "test", "parameters": {}}
        response = await service.process_request(request)
        assert response.success

    @pytest.mark.asyncio
    async def test_process_request_resource_limits(self, service):
        """Test resource limit handling."""
        await service.initialize()

        # Mock resource limiter to trigger limit
        service.resource_limiter.check_limit = MagicMock(return_value=False)

        request = {"action": "test", "parameters": {}}
        response = await service.process_request(request)
        assert not response.success
        assert "resource limit" in response.error.lower()
        assert service.resource_limit_exceeded == 1

    @pytest.mark.asyncio
    async def test_process_request_safety_violation(self, service):
        """Test safety violation handling."""
        await service.initialize()

        # Mock safety checker to trigger violation
        service.safety_checker.check_safety = MagicMock(
            return_value=(False, [MagicMock()])
        )

        request = {"action": "test", "parameters": {}}
        response = await service.process_request(request)
        assert not response.success
        assert "safety violation" in response.error.lower()
        assert service.safety_violations == 1

    @pytest.mark.asyncio
    async def test_handle_critical_violation(self, service):
        """Test critical violation handling."""
        await service.initialize()
        violation = MagicMock()
        violation.level = SafetyLevel.CRITICAL
        violation.description = "Test violation"
        violation.rule_id = "rule1"
        # Should raise SecurityViolationError
        with pytest.raises(SecurityViolationError):
            service._handle_critical_violation(violation)

    @pytest.mark.asyncio
    async def test_handle_violation(self, service):
        """Test regular violation handling."""
        await service.initialize()
        violation = MagicMock()
        violation.level = SafetyLevel.VIOLATION
        violation.description = "Test violation"
        violation.rule_id = "rule2"
        service._handle_violation(violation)
        assert service.safety_violations == 1

    @pytest.mark.asyncio
    async def test_handle_token_limit(self, service):
        """Test token limit handling."""
        await service.initialize()
        service._handle_token_limit(ResourceType.TOKENS, "ctx", 1000, 500, True)
        assert service.resource_limit_exceeded == 1

    @pytest.mark.asyncio
    async def test_handle_api_limit(self, service):
        """Test API limit handling."""
        await service.initialize()
        service._handle_api_limit(ResourceType.API_CALLS, "ctx", 100, 50, True)
        assert service.resource_limit_exceeded == 1

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check."""
        await service.initialize()
        response = await service.health_check()
        assert response.success
        assert "status" in response.data
        assert "components" in response.data
        assert "statistics" in response.data

    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, service):
        """Test health check when not initialized."""
        response = await service.health_check()
        assert not response.success
        assert "not initialized" in (response.error or "")

    @pytest.mark.asyncio
    async def test_error_handling_strategies(self, service):
        """Test error handling strategies."""
        await service.initialize()

        # Test security violation strategy
        error = SecurityViolationError("Test violation")
        strategy = service.error_handler.get_strategy(type(error))
        assert strategy[0] == RecoveryStrategy.ESCALATE
        assert strategy[1] == ErrorSeverity.HIGH

        # Test resource limit strategy
        error = ResourceLimitError("Test limit")
        strategy = service.error_handler.get_strategy(type(error))
        assert strategy[0] == RecoveryStrategy.THROTTLE
        assert strategy[1] == ErrorSeverity.HIGH
