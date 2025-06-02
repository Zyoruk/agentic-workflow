"""Tests for custom exceptions."""

from agentic_workflow.core.exceptions import (
    AgentError,
    AgenticWorkflowError,
    ConfigurationError,
    NotFoundError,
    ResourceLimitError,
    SecurityViolationError,
    ServiceError,
    TimeoutError,
    ValidationError,
)


class TestAgenticWorkflowError:
    """Test base exception class."""

    def test_base_error(self):
        """Test base error initialization."""
        error = AgenticWorkflowError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"

    def test_error_with_args(self):
        """Test error with additional arguments."""
        error = AgenticWorkflowError("Test error", "arg1", "arg2", key="value")
        assert str(error) == "('Test error', 'arg1', 'arg2')"
        assert error.args == ("Test error", "arg1", "arg2")
        assert error.message == "Test error"
        assert (
            getattr(error, "key", None) == "value"
        )  # Verify keyword argument is stored


class TestValidationError:
    """Test validation error."""

    def test_validation_error(self):
        """Test validation error initialization."""
        error = ValidationError("Invalid value", field="test_field", value=123)
        assert str(error) == "Invalid value"
        assert error.field == "test_field"
        assert error.value == 123


class TestResourceLimitError:
    """Test resource limit error."""

    def test_resource_limit_error(self):
        """Test resource limit error initialization."""
        error = ResourceLimitError(
            "Resource limit exceeded",
            severity="high",
            resource_type="memory",
            context="database",
            current=1024,
            limit=512,
        )
        assert str(error) == "Resource limit exceeded"
        assert error.severity == "high"
        assert error.resource_type == "memory"
        assert error.context == "database"
        assert error.current == 1024
        assert error.limit == 512


class TestConfigurationError:
    """Test configuration error."""

    def test_configuration_error(self):
        """Test configuration error initialization."""
        error = ConfigurationError("Invalid config", config_key="test_key")
        assert str(error) == "Invalid config"
        assert error.config_key == "test_key"


class TestServiceError:
    """Test service error."""

    def test_service_error(self):
        """Test service error initialization."""
        error = ServiceError(
            "Service failed",
            service_name="test_service",
            operation="test_operation",
        )
        assert str(error) == "Service failed"
        assert error.service_name == "test_service"
        assert error.operation == "test_operation"


class TestAgentError:
    """Test agent error."""

    def test_agent_error(self):
        """Test agent error initialization."""
        error = AgentError(
            "Agent failed",
            agent_id="test_agent",
            task_id="test_task",
        )
        assert str(error) == "Agent failed"
        assert error.agent_id == "test_agent"
        assert error.task_id == "test_task"


class TestSecurityViolationError:
    """Test security violation error."""

    def test_security_violation_error(self):
        """Test security violation error initialization."""
        error = SecurityViolationError(
            "Security violation",
            rule_id="test_rule",
            level="high",
        )
        assert str(error) == "Security violation"
        assert error.rule_id == "test_rule"
        assert error.level == "high"


class TestNotFoundError:
    """Test not found error."""

    def test_not_found_error(self):
        """Test not found error initialization."""
        error = NotFoundError(
            "Resource not found",
            resource_type="test_resource",
            resource_id="test_id",
        )
        assert str(error) == "Resource not found"
        assert error.resource_type == "test_resource"
        assert error.resource_id == "test_id"


class TestTimeoutError:
    """Test timeout error."""

    def test_timeout_error(self):
        """Test timeout error initialization."""
        error = TimeoutError(
            "Operation timed out",
            operation="test_operation",
            timeout=30.0,
        )
        assert str(error) == "Operation timed out"
        assert error.operation == "test_operation"
        assert error.timeout == 30.0
