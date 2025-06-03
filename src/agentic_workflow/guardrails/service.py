"""Guardrails service component for the agentic workflow system."""

import time
from typing import Any, Dict, List, Optional

from ..core.exceptions import SecurityViolationError
from ..core.interfaces import ComponentStatus, Service, ServiceResponse
from ..core.logging_config import get_logger
from .error_handling import ErrorHandler, ErrorSeverity, RecoveryStrategy
from .input_validation import InputValidator
from .resource_limits import ResourceLimiter, ResourceType
from .safety_checks import SafetyChecker, SafetyLevel, SafetyViolation

logger = get_logger(__name__)


class GuardrailsService(Service):
    """Service for handling guardrails and safety mechanisms."""

    def __init__(
        self, name: str = "guardrails_service", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize guardrails service.

        Args:
        name: Service name
        config: Service configuration
        """
        super().__init__(name, config)

        # Initialize components
        self.input_validator = InputValidator(
            strict_mode=self.config.get("strict_validation", True)
        )
        self.resource_limiter = ResourceLimiter()
        self.error_handler = ErrorHandler()
        self.safety_checker = SafetyChecker()

        # Service state
        self.initialized = False

        # Statistics
        self.validation_failures = 0
        self.resource_limit_exceeded = 0
        self.safety_violations = 0
        self.handled_errors = 0

        logger.info(f"Initialized guardrails service: {name}")

    async def initialize(self) -> None:
        """Initialize the guardrails service."""
        try:
            self.status = ComponentStatus.INITIALIZING

            # Register cross-component handlers
            self._register_handlers()

            self.initialized = True
            self.status = ComponentStatus.READY

            logger.info("Guardrails service initialized successfully")

        except Exception as e:
            self.status = ComponentStatus.ERROR
            logger.error(f"Failed to initialize guardrails service: {e}")
            raise

    def _register_handlers(self) -> None:
        """Register cross-component handlers."""
        # Register safety violation handlers
        self.safety_checker.register_violation_handler(
            SafetyLevel.CRITICAL, self._handle_critical_violation
        )
        self.safety_checker.register_violation_handler(
            SafetyLevel.VIOLATION, self._handle_violation
        )

        # Register resource limit callbacks
        self.resource_limiter.register_callback(
            ResourceType.TOKENS, self._handle_token_limit
        )
        self.resource_limiter.register_callback(
            ResourceType.API_CALLS, self._handle_api_limit
        )

        # Register error strategies
        from ..core.exceptions import ResourceLimitError, SecurityViolationError

        self.error_handler.register_strategy(
            SecurityViolationError, RecoveryStrategy.ESCALATE, ErrorSeverity.HIGH
        )
        self.error_handler.register_strategy(
            ResourceLimitError, RecoveryStrategy.THROTTLE, ErrorSeverity.HIGH
        )

    def _handle_critical_violation(self, violation: SafetyViolation) -> None:
        """Handle critical safety violations.

        Args:
        violation: Safety violation
        """
        logger.critical(f"Critical safety violation: {violation}")
        self.safety_violations += 1

        # Raise exception for critical violations
        raise SecurityViolationError(
            message=violation.description,
            rule_id=violation.rule_id,
            level=violation.level,
        )

    def _handle_violation(self, violation: SafetyViolation) -> None:
        """Handle non-critical safety violations.

        Args:
        violation: Safety violation
        """
        logger.warning(f"Safety violation: {violation}")
        self.safety_violations += 1

    def _handle_token_limit(
        self,
        resource_type: ResourceType,
        context: str,
        current: float,
        limit: float,
        is_exceeded: bool,
    ) -> None:
        """Handle token limit events.

        Args:
        resource_type: Type of resource
        context: Context identifier
        current: Current usage
        limit: Usage limit
        is_exceeded: Whether limit is exceeded
        """
        if is_exceeded:
            logger.warning(f"Token limit exceeded for {context}: {current}/{limit}")
            self.resource_limit_exceeded += 1

    def _handle_api_limit(
        self,
        resource_type: ResourceType,
        context: str,
        current: float,
        limit: float,
        is_exceeded: bool,
    ) -> None:
        """Handle API call limit events.

        Args:
        resource_type: Type of resource
        context: Context identifier
        current: Current usage
        limit: Usage limit
        is_exceeded: Whether limit is exceeded
        """
        if is_exceeded:
            logger.warning(f"API call limit exceeded for {context}: {current}/{limit}")
            self.resource_limit_exceeded += 1

    async def validate_input(
        self, data: Dict[str, Any], rules_map: Dict[str, List[str]]
    ) -> ServiceResponse:
        """Validate input data.

        Args:
            data: Input data
            rules_map: Validation rules mapping

        Returns:
            Service response
        """
        try:
            is_valid = self.input_validator.validate_dict(data, rules_map)

            if is_valid:
                return ServiceResponse(
                    success=True,
                    data={"valid": True},
                    metadata={"message": "Input validation successful"},
                )
            else:
                self.validation_failures += 1
                errors = self.input_validator.get_errors()

                return ServiceResponse(
                    success=False,
                    data={
                        "valid": False,
                        "errors": [
                            {"field": e.field, "message": str(e)} for e in errors
                        ],
                    },
                    error="Input validation failed",
                )

        except Exception as e:
            logger.error(f"Error in input validation: {e}")
            return ServiceResponse(
                success=False,
                data={"valid": False},
                error=f"Input validation error: {str(e)}",
            )

    async def check_safety(
        self, data: Any, context: Optional[Dict[str, Any]] = None
    ) -> ServiceResponse:
        """Check data for safety violations.

        Args:
            data: Data to check
            context: Additional context

        Returns:
            Service response
        """
        try:
            is_safe, violations = self.safety_checker.check_safety(data, context)

            return ServiceResponse(
                success=is_safe,
                data={
                    "is_safe": is_safe,
                    "violations": [v.to_dict() for v in violations],
                },
                metadata={"message": "Safety check completed"},
            )

        except Exception as e:
            logger.error(f"Error in safety check: {e}")
            return ServiceResponse(
                success=False,
                data={"is_safe": False},
                error=f"Safety check error: {str(e)}",
            )

    async def track_resource(
        self,
        context: str,
        resource_type: ResourceType,
        amount: float = 1.0,
        unit: str = "",
    ) -> ServiceResponse:
        """Track resource usage.

        Args:
            context: Context identifier
            resource_type: Type of resource
            amount: Amount to increment
            unit: Unit of measurement

        Returns:
            Service response
        """
        try:
            is_within_limit = self.resource_limiter.increment_usage(
                context, resource_type, amount, unit
            )

            usage = self.resource_limiter.get_usage(context, resource_type, unit)

            if not usage:
                return ServiceResponse(
                    success=False,
                    data={"within_limit": is_within_limit},
                    error=f"Unknown resource: {resource_type.value} for {context}",
                )

            return ServiceResponse(
                success=is_within_limit,
                data={
                    "within_limit": is_within_limit,
                    "usage": {
                        "current": usage.current,
                        "limit": usage.limit,
                        "percentage": usage.percentage,
                        "unit": usage.unit,
                    },
                },
                metadata={"message": "Resource usage tracked"},
            )

        except Exception as e:
            logger.error(f"Error tracking resource usage: {e}")
            return ServiceResponse(
                success=False,
                data={"within_limit": False},
                error=f"Resource tracking error: {str(e)}",
            )

    async def handle_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ServiceResponse:
        """Handle an error.

        Args:
            error: Exception to handle
            context: Additional context

        Returns:
            Service response
        """
        try:
            result = self.error_handler.handle_error(error, context)
            self.handled_errors += 1

            return ServiceResponse(
                success=result.get("handled", False),
                data=result,
                metadata={"message": "Error handling completed"},
            )

        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return ServiceResponse(
                success=False,
                data={"handled": False},
                error=f"Error handler error: {str(e)}",
            )

    async def safely_execute(
        self,
        func: Any,
        *args: Any,
        error_context: Optional[Dict[str, Any]] = None,
        fallback_value: Any = None,
        **kwargs: Any,
    ) -> ServiceResponse:
        """Safely execute a function with error handling.

        Args:
            func: Function to execute
            *args: Positional arguments
            error_context: Context for error handling
            fallback_value: Value to return on error
            **kwargs: Keyword arguments

        Returns:
            Service response
        """
        try:
            result = self.error_handler.safely_execute(
                func,
                *args,
                error_context=error_context,
                fallback_value=fallback_value,
                **kwargs,
            )

            # Check if result is the fallback value due to error
            is_fallback = result == fallback_value and not kwargs.get(
                "expected_fallback", False
            )

            return ServiceResponse(
                success=not is_fallback,
                data={"result": result, "is_fallback": is_fallback},
                metadata={"message": "Function executed safely"},
            )

        except Exception as e:
            logger.error(f"Error in safe execution: {e}")
            return ServiceResponse(
                success=False,
                data={"result": fallback_value, "is_fallback": True},
                error=f"Safe execution error: {str(e)}",
            )

    async def get_stats(self) -> ServiceResponse:
        """Get service statistics.

        Returns:
            Service response with statistics
        """
        try:
            stats: Dict[str, Any] = {
                "validation_failures": self.validation_failures,
                "resource_limit_exceeded": self.resource_limit_exceeded,
                "safety_violations": self.safety_violations,
                "handled_errors": self.handled_errors,
                "status": self.status.value,
                "initialized": self.initialized,
            }

            # Add resource usage statistics
            resource_stats: Dict[str, List[Dict[str, Any]]] = {}
            resource_usages = self.resource_limiter.get_all_usages()
            for context, usages in resource_usages.items():
                resource_stats[context] = [
                    {
                        "resource_type": usage.resource_type.value,
                        "current": usage.current,
                        "limit": usage.limit,
                        "percentage": usage.percentage,
                        "unit": usage.unit,
                    }
                    for usage in usages
                ]

            stats["resources"] = resource_stats

            return ServiceResponse(
                success=True,
                data=stats,
                metadata={"timestamp": time.time()},
            )

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return ServiceResponse(
                success=False,
                data={},
                error=f"Statistics error: {str(e)}",
            )

    async def close(self) -> None:
        """Close the guardrails service and cleanup resources."""
        # Nothing to clean up
        logger.info("Guardrails service closed")

    async def start(self) -> None:
        """Start the guardrails service."""
        try:
            if not self.initialized:
                await self.initialize()

            self.status = ComponentStatus.RUNNING
            logger.info("Guardrails service started")

        except Exception as e:
            self.status = ComponentStatus.ERROR
            logger.error(f"Failed to start guardrails service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the guardrails service."""
        try:
            self.status = ComponentStatus.STOPPED
            logger.info("Guardrails service stopped")

        except Exception as e:
            logger.error(f"Error stopping guardrails service: {e}")
            self.status = ComponentStatus.ERROR

    async def health_check(self) -> ServiceResponse:
        """Check guardrails service health."""
        try:
            if not self.initialized:
                return ServiceResponse(
                    success=False,
                    error="Guardrails service not initialized",
                    data={"status": self.status.value},
                )

            # Get component statuses
            components = {
                "input_validator": True,  # Simple component, always healthy
                "resource_limiter": True,  # Simple component, always healthy
                "error_handler": True,  # Simple component, always healthy
                "safety_checker": True,  # Simple component, always healthy
            }

            # Get statistics
            stats = await self.get_stats()

            return ServiceResponse(
                success=True,
                data={
                    "status": "healthy",
                    "components": components,
                    "statistics": stats.data,
                },
                metadata={"service": self.name},
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ServiceResponse(
                success=False,
                error=f"Health check failed: {e}",
                metadata={"service": self.name},
            )

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a guardrails service request.

        Args:
            request: Request data with action and parameters

        Returns:
            Service response
        """
        try:
            if not self.initialized:
                return ServiceResponse(
                    success=False,
                    error="Guardrails service not initialized",
                )

            action = request.get("action")
            params = request.get("parameters", {})

            if action == "test":
                # Handle test action for validation
                if params is None:
                    self.validation_failures += 1
                    return ServiceResponse(
                        success=False,
                        error="Validation failed: parameters cannot be None",
                    )

                # Check resource limits
                if not self.resource_limiter.check_limit("test", ResourceType.TOKENS):
                    self.resource_limit_exceeded += 1
                    return ServiceResponse(
                        success=False,
                        error="Resource limit exceeded",
                    )

                # Check safety
                is_safe, violations = self.safety_checker.check_safety(params)
                if not is_safe:
                    self.safety_violations += 1
                    return ServiceResponse(
                        success=False,
                        error="Safety violation detected",
                    )

                return ServiceResponse(success=True)

            elif action == "validate_input":
                return await self.validate_input(
                    params.get("data", {}), params.get("rules", {})
                )
            elif action == "check_safety":
                return await self.check_safety(
                    params.get("data"), params.get("context")
                )
            elif action == "track_resource":
                return await self.track_resource(
                    params.get("context", ""),
                    params.get("resource_type"),
                    params.get("amount", 1.0),
                    params.get("unit", ""),
                )
            elif action == "handle_error":
                return await self.handle_error(
                    params.get("error"), params.get("context")
                )
            elif action == "safely_execute":
                return await self.safely_execute(
                    params.get("func"),
                    *params.get("args", []),
                    error_context=params.get("error_context"),
                    fallback_value=params.get("fallback_value"),
                    **params.get("kwargs", {}),
                )
            elif action == "get_stats":
                return await self.get_stats()
            else:
                return ServiceResponse(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Failed to process request: {e}")
            return ServiceResponse(
                success=False,
                error=f"Request processing failed: {e}",
            )
