"""Unit tests for helper functions."""

from typing import Any, Dict

import pytest

from agentic_workflow.utils.helpers import format_response, validate_config


@pytest.mark.unit
def test_format_response_with_defaults() -> None:
    """Test format_response with default parameters."""
    data = {"message": "Hello World"}
    result = format_response(data)

    expected = {
        "status": "success",
        "data": {"message": "Hello World"},
        "timestamp": "2024-01-01T00:00:00Z",
    }

    assert result == expected


@pytest.mark.unit
def test_format_response_with_custom_status() -> None:
    """Test format_response with custom status."""
    data = {"error": "Something went wrong"}
    result = format_response(data, status="error")

    expected = {
        "status": "error",
        "data": {"error": "Something went wrong"},
        "timestamp": "2024-01-01T00:00:00Z",
    }

    assert result == expected


@pytest.mark.unit
def test_validate_config_valid() -> None:
    """Test validate_config with valid configuration."""
    config: Dict[str, Any] = {
        "api_key": "test-key",
        "database_url": "postgres://localhost:5432/test",
        "extra_param": "value",
    }

    assert validate_config(config) is True


@pytest.mark.unit
def test_validate_config_missing_api_key() -> None:
    """Test validate_config with missing api_key."""
    config: Dict[str, str] = {"database_url": "postgres://localhost:5432/test"}

    assert validate_config(config) is False


@pytest.mark.unit
def test_validate_config_missing_database_url() -> None:
    """Test validate_config with missing database_url."""
    config: Dict[str, str] = {"api_key": "test-key"}

    assert validate_config(config) is False


@pytest.mark.unit
def test_validate_config_empty() -> None:
    """Test validate_config with empty configuration."""
    config: Dict[str, Any] = {}

    assert validate_config(config) is False
