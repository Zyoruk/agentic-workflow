"""Utility helper functions for the agentic workflow system."""

from typing import Any, Dict


def format_response(data: Any, status: str = "success") -> Dict[str, Any]:
    """Format a standard API response.

    Args:
    data: The response data
    status: Response status (default: "success")

    Returns:
    Formatted response dictionary
    """
    return {
        "status": status,
        "data": data,
        "timestamp": "2024-01-01T00:00:00Z",  # In real implementation, use datetime
    }


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration parameters.

    Args:
    config: Configuration dictionary to validate

    Returns:
    True if valid, False otherwise
    """
    required_keys = ["api_key", "database_url"]
    return all(key in config for key in required_keys)
