"""Unit tests for ErrorHandler and error handling logic."""

from agentic_workflow.guardrails.error_handling import (
    ErrorHandler,
    ErrorSeverity,
    RecoveryStrategy,
)


class DummyError(Exception):
    """Dummy error for testing."""

    pass


def test_register_and_get_strategy():
    handler = ErrorHandler()
    handler.register_strategy(ValueError, RecoveryStrategy.THROTTLE, ErrorSeverity.HIGH)
    strategy, severity = handler.get_strategy(ValueError)
    assert strategy == RecoveryStrategy.THROTTLE
    assert severity == ErrorSeverity.HIGH

    # For any unregistered error type, expect the default Exception strategy
    strategy, severity = handler.get_strategy(TypeError)
    assert strategy == RecoveryStrategy.FALLBACK
    assert severity == ErrorSeverity.MEDIUM


def test_handle_error_throttle():
    handler = ErrorHandler()
    handler.register_strategy(DummyError, RecoveryStrategy.THROTTLE, ErrorSeverity.HIGH)
    result = handler.handle_error(DummyError("fail"), context={"delay": 2.0})
    assert result["handled"]
    assert result["action"] == "throttle"
    assert result["delay"] == 2.0


def test_handle_error_escalate():
    handler = ErrorHandler()
    handler.register_strategy(DummyError, RecoveryStrategy.ESCALATE, ErrorSeverity.HIGH)
    result = handler.handle_error(DummyError("fail"))
    assert not result["handled"]
    assert result["action"] == "escalate"
    assert result["escalation_level"] == ErrorSeverity.HIGH.value


def test_handle_error_restart():
    handler = ErrorHandler()
    handler.register_strategy(DummyError, RecoveryStrategy.RESTART, ErrorSeverity.LOW)
    result = handler.handle_error(DummyError("fail"), context={"component": "foo"})
    assert result["handled"]
    assert result["action"] == "restart"
    assert result["component"] == "foo"


def test_handle_error_ignore():
    handler = ErrorHandler()
    handler.register_strategy(DummyError, RecoveryStrategy.IGNORE, ErrorSeverity.LOW)
    result = handler.handle_error(DummyError("fail"))
    assert result["handled"]
    assert result["action"] == "ignore"


def test_handle_error_circuit_breaker():
    handler = ErrorHandler()
    handler.register_strategy(
        DummyError, RecoveryStrategy.CIRCUIT_BREAKER, ErrorSeverity.HIGH
    )
    # Simulate error count below threshold
    handler.error_counts["DummyError"] = 2
    result = handler.handle_error(DummyError("fail"), context={"threshold": 5})
    assert not result["handled"]
    assert result["action"] == "circuit_closed"
    # Simulate error count above threshold
    handler.error_counts["DummyError"] = 6
    result = handler.handle_error(DummyError("fail"), context={"threshold": 5})
    assert result["handled"]
    assert result["action"] == "circuit_open"


def test_handle_error_custom_strategy():
    handler = ErrorHandler()
    handler.register_strategy(DummyError, RecoveryStrategy.CUSTOM, ErrorSeverity.LOW)
    result = handler.handle_error(DummyError("fail"))
    assert not result["handled"]
    assert result["action"] == "unknown_strategy"


def test_clear_error_counts():
    handler = ErrorHandler()
    handler.error_counts["DummyError"] = 3
    handler.clear_error_counts()
    assert handler.error_counts == {}
