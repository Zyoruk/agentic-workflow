"""Example integration test."""

import pytest


@pytest.mark.integration
def test_database_connection() -> None:
    """Test database connectivity."""
    # Example integration test - would test actual database connection
    # For now, just verify the test framework works
    assert True


@pytest.mark.integration
@pytest.mark.slow
def test_slow_integration() -> None:
    """Test slow integration functionality."""
    # Example of a slow test that can be skipped with -m "not slow"
    assert True
