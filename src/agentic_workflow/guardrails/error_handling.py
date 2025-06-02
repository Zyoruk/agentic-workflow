"""Error handling and recovery mechanisms for the agentic workflow system."""

import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Strategies for recovering from errors."""

    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    TIMEOUT = "timeout"
    THROTTLE = "throttle"
    IGNORE = "ignore"
    ESCALATE = "escalate"
    RESTART = "restart"
    CUSTOM = "custom"


class ErrorHandler:
    """Error handling and recovery for system resilience."""

    def __init__(self) -> None:
        """Initialize error handler."""
        self.error_counts: Dict[str, int] = {}
        self.strategies: Dict[Type[Exception], RecoveryStrategy] = {}
        self.severity_levels: Dict[Type[Exception], ErrorSeverity] = {}
        self.handlers: Dict[RecoveryStrategy, Callable] = {}
        self.custom_handlers: Dict[Type[Exception], Callable] = {}
        self.max_retries: Dict[Type[Exception], int] = {}

        # Register default strategies
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register default error handling strategies."""
        # Network errors
        self.register_strategy(
            ConnectionError, RecoveryStrategy.RETRY, ErrorSeverity.MEDIUM
        )
        self.register_strategy(
            TimeoutError, RecoveryStrategy.RETRY, ErrorSeverity.MEDIUM
        )

        # Resource errors
        from ..core.exceptions import ResourceLimitError

        self.register_strategy(
            ResourceLimitError, RecoveryStrategy.THROTTLE, ErrorSeverity.HIGH
        )

        # Default fallback for generic exceptions
        self.register_strategy(
            Exception, RecoveryStrategy.FALLBACK, ErrorSeverity.MEDIUM
        )

        # Set default retry limits
        self.set_max_retries(ConnectionError, 3)
        self.set_max_retries(TimeoutError, 2)

    def register_strategy(
        self,
        exception_type: Type[Exception],
        strategy: RecoveryStrategy,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> None:
        """Register a recovery strategy for an exception type.

        Args:
            exception_type: Type of exception
            strategy: Recovery strategy
            severity: Error severity
        """
        self.strategies[exception_type] = strategy
        self.severity_levels[exception_type] = severity
        logger.debug(
            f"Registered {strategy.value} strategy for {exception_type.__name__} "
            f"with {severity.value} severity"
        )

    def register_handler(
        self, strategy: RecoveryStrategy, handler_func: Callable
    ) -> None:
        """Register a handler function for a recovery strategy.

        Args:
            strategy: Recovery strategy
            handler_func: Handler function
        """
        self.handlers[strategy] = handler_func
        logger.debug(f"Registered handler for {strategy.value} strategy")

    def register_custom_handler(
        self, exception_type: Type[Exception], handler_func: Callable
    ) -> None:
        """Register a custom handler for a specific exception type.

        Args:
            exception_type: Type of exception
            handler_func: Handler function
        """
        self.custom_handlers[exception_type] = handler_func
        logger.debug(f"Registered custom handler for {exception_type.__name__}")

    def set_max_retries(
        self, exception_type: Type[Exception], max_retries: int
    ) -> None:
        """Set maximum retries for an exception type.

        Args:
            exception_type: Type of exception
            max_retries: Maximum number of retries
        """
        self.max_retries[exception_type] = max_retries

    def get_retry_count(self, exception_type: Type[Exception]) -> int:
        """Get current retry count for an exception type.

        Args:
            exception_type: Type of exception

        Returns:
            Current retry count
        """
        return self.error_counts.get(exception_type.__name__, 0)

    def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an error using the registered strategy.

        Args:
            error: Exception to handle
            context: Optional context information

        Returns:
            Dictionary with handling results
        """
        context = context or {}
        error_type = type(error)
        error_name = error_type.__name__

        # Increment error count
        self.error_counts[error_name] = self.error_counts.get(error_name, 0) + 1

        # Find the most specific matching error type
        strategy = None
        severity = None

        for exc_type, strat in self.strategies.items():
            if isinstance(error, exc_type):
                if strategy is None or issubclass(exc_type, error_type):
                    strategy = strat
                    severity = self.severity_levels.get(exc_type, ErrorSeverity.MEDIUM)

        if not strategy:
            strategy = RecoveryStrategy.ESCALATE
            severity = ErrorSeverity.HIGH

        # Log the error
        self._log_error(error, strategy, severity, context)

        # Check if we have a custom handler
        for exc_type, handler in self.custom_handlers.items():
            if isinstance(error, exc_type):
                logger.info(f"Using custom handler for {error_name}")
                try:
                    result = handler(error, context)
                    return {
                        "error": error,
                        "error_type": error_name,
                        "strategy": strategy.value,
                        "severity": (
                            severity.value if severity else ErrorSeverity.MEDIUM.value
                        ),
                        "handled": True,
                        "action": result.get("action", "custom"),
                        **result,
                    }
                except Exception as e:
                    logger.error(f"Custom handler failed: {e}")
                    # Continue with standard strategies

        # Execute standard strategy
        if strategy in self.handlers:
            try:
                result = self.handlers[strategy](error, context)
                return {
                    "error": error,
                    "error_type": error_name,
                    "strategy": strategy.value,
                    "severity": (
                        severity.value if severity else ErrorSeverity.MEDIUM.value
                    ),
                    "handled": True,
                    "action": result.get("action", strategy.value),
                    **result,
                }
            except Exception as e:
                logger.error(f"Strategy handler failed: {e}")

        # Apply default behavior based on strategy
        result = self._apply_default_strategy(error, strategy, severity, context)

        return {
            "error": error,
            "error_type": error_name,
            "strategy": strategy.value,
            "severity": severity.value if severity else ErrorSeverity.MEDIUM.value,
            "handled": result.get("handled", False),
            "action": result.get("action", strategy.value),
            **result,
        }

    def _log_error(
        self,
        error: Exception,
        strategy: RecoveryStrategy,
        severity: Optional[ErrorSeverity],
        context: Dict[str, Any],
    ) -> None:
        """Log error with appropriate level based on severity.

        Args:
            error: Exception that occurred
            strategy: Recovery strategy
            severity: Error severity
            context: Context information
        """
        error_type = type(error).__name__
        error_msg = str(error)
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())

        # Default to MEDIUM severity if None
        if severity is None:
            severity = ErrorSeverity.MEDIUM

        log_message = (
            f"Error: {error_type}: {error_msg} | "
            f"Strategy: {strategy.value} | "
            f"Context: {context_str}"
        )

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
            logger.critical(f"Traceback: {traceback.format_exc()}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message)
            logger.error(f"Traceback: {traceback.format_exc()}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:  # LOW
            logger.info(log_message)

    def _apply_default_strategy(
        self,
        error: Exception,
        strategy: RecoveryStrategy,
        severity: Optional[ErrorSeverity],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply default behavior for a strategy.

        Args:
            error: Exception that occurred
            strategy: Recovery strategy
            severity: Error severity
            context: Context information

        Returns:
            Strategy result
        """
        error_type = type(error)

        # Default to MEDIUM severity if None
        if severity is None:
            severity = ErrorSeverity.MEDIUM

        if strategy == RecoveryStrategy.RETRY:
            # Check retry count
            retry_count = self.get_retry_count(error_type)
            max_retries = self.max_retries.get(error_type, 3)

            if retry_count <= max_retries:
                return {
                    "handled": True,
                    "action": "retry",
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                }
            else:
                logger.warning(
                    f"Max retries ({max_retries}) exceeded for {error_type.__name__}"
                )
                return {
                    "handled": False,
                    "action": "max_retries_exceeded",
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                }

        elif strategy == RecoveryStrategy.FALLBACK:
            fallback_value = context.get("fallback_value")
            return {
                "handled": True,
                "action": "fallback",
                "fallback_value": fallback_value,
            }

        elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            # Simple circuit breaker implementation
            error_count = self.error_counts.get(error_type.__name__, 0)
            threshold = context.get("threshold", 5)

            if error_count >= threshold:
                return {
                    "handled": True,
                    "action": "circuit_open",
                    "error_count": error_count,
                    "threshold": threshold,
                }
            return {
                "handled": False,
                "action": "circuit_closed",
                "error_count": error_count,
                "threshold": threshold,
            }

        elif strategy == RecoveryStrategy.THROTTLE:
            return {
                "handled": True,
                "action": "throttle",
                "delay": context.get("delay", 1.0),
            }

        elif strategy == RecoveryStrategy.IGNORE:
            return {"handled": True, "action": "ignore"}

        elif strategy == RecoveryStrategy.ESCALATE:
            return {
                "handled": False,
                "action": "escalate",
                "escalation_level": severity.value,
            }

        elif strategy == RecoveryStrategy.RESTART:
            return {
                "handled": True,
                "action": "restart",
                "component": context.get("component", "unknown"),
            }

        else:  # CUSTOM or unknown
            return {"handled": False, "action": "unknown_strategy"}

    def clear_error_counts(self) -> None:
        """Clear all error counts."""
        self.error_counts.clear()

    def safely_execute(
        self,
        func: Callable,
        *args: Any,
        error_context: Optional[Dict[str, Any]] = None,
        fallback_value: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with error handling.

        Args:
            func: Function to execute
            *args: Positional arguments
            error_context: Context for error handling
            fallback_value: Value to return on error
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback value
        """
        context = error_context or {}
        context["fallback_value"] = fallback_value

        try:
            return func(*args, **kwargs)
        except Exception as e:
            result = self.handle_error(e, context)

            if result.get("handled", False):
                action = result.get("result", {}).get("action")

                if action == "retry":
                    # Simple retry (in production, consider exponential backoff)
                    logger.info(
                        f"Retrying function call (attempt {result['result']['retry_count']})"
                    )
                    try:
                        return func(*args, **kwargs)
                    except Exception as retry_e:
                        logger.warning(f"Retry failed: {retry_e}")

                elif action == "fallback":
                    logger.info(f"Using fallback value: {fallback_value}")
                    return fallback_value

            # If not handled or no special action, return fallback
            return fallback_value

    def get_strategy(
        self, exception_type: Type[Exception]
    ) -> tuple[RecoveryStrategy, ErrorSeverity]:
        """Get the recovery strategy and severity for an exception type.

        Args:
            exception_type: Type of exception

        Returns:
            Tuple of (strategy, severity)
        """
        # Check for direct match
        if exception_type in self.strategies:
            return self.strategies[exception_type], self.severity_levels[exception_type]

        # Check if exception is a subclass of any registered type
        for exc_type, strategy in self.strategies.items():
            if issubclass(exception_type, exc_type):
                return strategy, self.severity_levels[exc_type]

        # Default to ESCALATE for unknown types
        return RecoveryStrategy.ESCALATE, ErrorSeverity.HIGH
