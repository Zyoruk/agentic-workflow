"""Custom exceptions for the agentic workflow system."""

from typing import Any, Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class AgenticWorkflowError(Exception):
    """Base exception for all agentic workflow errors."""

    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Initialize base error.

        Args:
            message: Error message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.message = message
        super().__init__(message, *args, **kwargs)


class ValidationError(AgenticWorkflowError):
    """Exception raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: Value that failed validation
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.field = field
        self.value = value
        super().__init__(message, *args, **kwargs)


class ResourceLimitError(AgenticWorkflowError):
    """Exception raised when a resource limit is exceeded."""

    def __init__(
        self,
        message: str,
        severity: Any = None,  # Avoid circular import with ErrorSeverity
        resource_type: Any = None,  # Avoid circular import with ResourceType
        context: Optional[str] = None,
        current: Optional[float] = None,
        limit: Optional[float] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize resource limit error.

        Args:
            message: Error message
            severity: Error severity level
            resource_type: Type of resource that exceeded the limit
            context: Context identifier (e.g. "openai", "database")
            current: Current usage value
            limit: Maximum limit value
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.severity = severity
        self.resource_type = resource_type
        self.context = context
        self.current = current
        self.limit = limit
        super().__init__(message, *args, **kwargs)


class ConfigurationError(AgenticWorkflowError):
    """Exception raised when there is a configuration error."""

    def __init__(
        self, message: str, config_key: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.config_key = config_key
        super().__init__(message, *args, **kwargs)


class ServiceError(AgenticWorkflowError):
    """Exception raised when a service encounters an error."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize service error.

        Args:
            message: Error message
            service_name: Name of the service
            operation: Operation that failed
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.service_name = service_name
        self.operation = operation
        super().__init__(message, *args, **kwargs)


class AgentError(AgenticWorkflowError):
    """Exception raised when an agent encounters an error."""

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize agent error.

        Args:
            message: Error message
            agent_id: ID of the agent
            task_id: ID of the task being executed
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.agent_id = agent_id
        self.task_id = task_id
        super().__init__(message, *args, **kwargs)


class SecurityViolationError(AgenticWorkflowError):
    """Exception raised when a security violation is detected."""

    def __init__(
        self,
        message: str,
        rule_id: Optional[str] = None,
        level: Any = None,  # Avoid circular import with SafetyLevel
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize security violation error.

        Args:
            message: Error message
            rule_id: ID of the security rule that was violated
            level: Severity level of the violation
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.rule_id = rule_id
        self.level = level
        super().__init__(message, *args, **kwargs)


class NotFoundError(AgenticWorkflowError):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize not found error.

        Args:
            message: Error message
            resource_type: Type of resource
            resource_id: ID of the resource
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, *args, **kwargs)


class TimeoutError(AgenticWorkflowError):
    """Exception raised when an operation times out."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error message
            operation: Operation that timed out
            timeout: Timeout value in seconds
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.operation = operation
        self.timeout = timeout
        super().__init__(message, *args, **kwargs)
