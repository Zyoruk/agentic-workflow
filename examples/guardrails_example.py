#!/usr/bin/env python3
"""Example demonstrating the guardrails and safety systems."""

import asyncio
import os
import sys
import time
from typing import Any, Dict

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agentic_workflow.core.logging_config import get_logger, setup_logging
from src.agentic_workflow.guardrails.error_handling import ErrorHandler, RecoveryStrategy
from src.agentic_workflow.guardrails.input_validation import InputValidator
from src.agentic_workflow.guardrails.resource_limits import ResourceLimiter, ResourceType
from src.agentic_workflow.guardrails.safety_checks import SafetyChecker, SafetyLevel
from src.agentic_workflow.guardrails.service import GuardrailsService


logger = get_logger(__name__)


def setup_logging():
    """Set up logging for the example."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def demonstrate_input_validation():
    """Demonstrate input validation."""
    logger.info("\n=== Input Validation Demo ===")

    # Create input validator
    validator = InputValidator()

    # Validate simple values
    email = "user@example.com"
    logger.info(f"Validating email: {email}")
    is_valid = validator.validate("email", email, ["email"])
    logger.info(f"Valid email? {is_valid}")

    bad_email = "not-an-email"
    logger.info(f"Validating bad email: {bad_email}")
    try:
        is_valid = validator.validate("email", bad_email, ["email"])
        logger.info(f"Valid email? {is_valid}")
    except Exception as e:
        logger.info(f"Validation failed as expected: {e}")

    # Validate a dictionary
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    }

    rules_map = {
        "name": ["non_empty_string"],
        "email": ["email"],
        "age": ["positive_number"]
    }

    logger.info(f"Validating user data: {user_data}")
    is_valid = validator.validate_dict(user_data, rules_map)
    logger.info(f"Valid user data? {is_valid}")

    # Invalid data
    invalid_data = {
        "name": "",  # Empty name
        "email": "invalid-email",
        "age": -5  # Negative age
    }

    logger.info(f"Validating invalid data: {invalid_data}")
    validator.strict_mode = False  # Don't raise exceptions
    is_valid = validator.validate_dict(invalid_data, rules_map)
    logger.info(f"Valid data? {is_valid}")
    logger.info(f"Validation errors: {[str(e) for e in validator.get_errors()]}")


async def demonstrate_resource_limits():
    """Demonstrate resource limit enforcement."""
    logger.info("\n=== Resource Limits Demo ===")

    # Create resource limiter
    limiter = ResourceLimiter()

    # Set custom limits
    limiter.set_limit("openai", ResourceType.TOKENS, 1000, "per_minute")
    limiter.set_limit("user_request", ResourceType.TIME, 5, "seconds")

    # Track token usage
    logger.info("Tracking token usage...")
    for i in range(5):
        tokens = 250
        within_limit = limiter.increment_usage(
            "openai", ResourceType.TOKENS, tokens, "per_minute"
        )
        usage = limiter.get_usage("openai", ResourceType.TOKENS, "per_minute")
        logger.info(
            f"Added {tokens} tokens: {usage.current}/{usage.limit} "
            f"({usage.percentage:.1f}%) - Within limit? {within_limit}"
        )

    # Demonstrate limit exceeded
    logger.info("Exceeding the limit...")
    tokens = 500
    within_limit = limiter.increment_usage(
        "openai", ResourceType.TOKENS, tokens, "per_minute"
    )
    usage = limiter.get_usage("openai", ResourceType.TOKENS, "per_minute")
    logger.info(
        f"Added {tokens} tokens: {usage.current}/{usage.limit} "
        f"({usage.percentage:.1f}%) - Within limit? {within_limit}"
    )

    # Reset usage
    logger.info("Resetting usage...")
    limiter.reset_usage("openai", ResourceType.TOKENS)
    usage = limiter.get_usage("openai", ResourceType.TOKENS, "per_minute")
    logger.info(
        f"After reset: {usage.current}/{usage.limit} "
        f"({usage.percentage:.1f}%)"
    )


async def demonstrate_error_handling():
    """Demonstrate error handling."""
    logger.info("\n=== Error Handling Demo ===")

    # Create error handler
    handler = ErrorHandler()

    # Define functions that might fail
    def divide(a, b):
        return a / b

    def access_dict(d, key):
        return d[key]

    # Handle a division by zero error
    logger.info("Handling division by zero...")
    try:
        result = divide(10, 0)
    except Exception as e:
        result = handler.handle_error(e)
        logger.info(f"Error handled: {result}")

    # Safely execute a function that might fail
    logger.info("Safely executing functions...")

    # Should succeed
    result = handler.safely_execute(divide, 10, 2, fallback_value="ERROR")
    logger.info(f"10 / 2 = {result}")

    # Should fail and return fallback
    result = handler.safely_execute(divide, 10, 0, fallback_value="ERROR")
    logger.info(f"10 / 0 = {result}")

    # Handle KeyError
    logger.info("Handling KeyError...")
    data = {"a": 1, "b": 2}

    # Register a custom strategy for KeyError
    handler.register_strategy(KeyError, RecoveryStrategy.FALLBACK)

    # Should return fallback for missing key
    result = handler.safely_execute(
        access_dict, data, "c", fallback_value="KEY_NOT_FOUND"
    )
    logger.info(f"data['c'] = {result}")


async def demonstrate_safety_checks():
    """Demonstrate safety checks."""
    logger.info("\n=== Safety Checks Demo ===")

    # Create safety checker
    checker = SafetyChecker()

    # Safe content
    safe_content = "This is a safe message about machine learning."
    logger.info(f"Checking safe content: {safe_content}")
    is_safe, violations = checker.check_safety(safe_content)
    logger.info(f"Is safe? {is_safe}, Violations: {len(violations)}")

    # Unsafe content with harmful keywords
    unsafe_content = "Let me hack into the system to exploit a vulnerability."
    logger.info(f"Checking unsafe content: {unsafe_content}")
    is_safe, violations = checker.check_safety(unsafe_content)
    logger.info(f"Is safe? {is_safe}, Violations: {len(violations)}")
    if violations:
        logger.info(f"Violation: {violations[0]}")

    # Code with dangerous imports
    code = """
import os
import sys
import subprocess

def run_command(cmd):
    return subprocess.check_output(cmd, shell=True)
    """
    logger.info("Checking code with dangerous imports")
    is_safe, violations = checker.check_safety(code)
    logger.info(f"Is safe? {is_safe}, Violations: {len(violations)}")
    if violations:
        logger.info(f"Violation: {violations[0]}")

    # Same code but with imports allowed in context
    logger.info("Checking code with context allowing imports")
    is_safe, violations = checker.check_safety(
        code, {"allow_system_imports": True}
    )
    logger.info(f"Is safe? {is_safe}, Violations: {len(violations)}")


async def demonstrate_guardrails_service():
    """Demonstrate the guardrails service."""
    logger.info("\n=== Guardrails Service Demo ===")

    # Create guardrails service
    service = GuardrailsService()
    await service.initialize()

    # Validate input
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    }

    rules_map = {
        "name": ["non_empty_string"],
        "email": ["email"],
        "age": ["positive_number"]
    }

    logger.info("Validating user data with service")
    response = await service.validate_input(user_data, rules_map)
    logger.info(f"Response: {response.status} - {response.message}")
    logger.info(f"Data: {response.data}")

    # Check safety
    content = "This is a safe message."
    logger.info(f"Checking content safety: {content}")
    response = await service.check_safety(content)
    logger.info(f"Response: {response.status} - {response.message}")
    logger.info(f"Is safe? {response.data.get('is_safe', False)}")

    unsafe_content = "Let me hack into the system to steal data."
    logger.info(f"Checking unsafe content: {unsafe_content}")
    response = await service.check_safety(unsafe_content)
    logger.info(f"Response: {response.status} - {response.message}")
    logger.info(f"Is safe? {response.data.get('is_safe', False)}")
    logger.info(f"Violations: {len(response.data.get('violations', []))}")

    # Track resource usage
    logger.info("Tracking token usage with service")
    response = await service.track_resource(
        "openai", ResourceType.TOKENS, 500, "per_minute"
    )
    logger.info(f"Response: {response.status} - {response.message}")
    logger.info(f"Usage: {response.data.get('usage', {})}")

    # Get statistics
    logger.info("Getting service statistics")
    response = await service.get_stats()
    logger.info(f"Response: {response.status} - {response.message}")
    logger.info(f"Statistics available: {list(response.data.keys())}")


async def main():
    """Main function demonstrating the guardrails system."""
    # Setup logging
    setup_logging()

    logger.info("🛡️ Starting Guardrails and Safety Systems Demonstration")

    try:
        # Run demonstrations
        await demonstrate_input_validation()
        await demonstrate_resource_limits()
        await demonstrate_error_handling()
        await demonstrate_safety_checks()
        await demonstrate_guardrails_service()

        logger.info("\n🎉 Guardrails demonstration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
