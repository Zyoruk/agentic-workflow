"""Example unit test."""

import pytest


def example_function(text: str) -> str:
    """Example function for testing."""
    return f"{text}_processed"


def test_example_function() -> None:
    """Test example function."""
    result = example_function("test")
    assert result == "test_processed"


@pytest.mark.asyncio
async def test_async_example() -> None:
    """Test async functionality."""
    # Example async test
    assert True


@pytest.mark.unit
def test_unit_marker() -> None:
    """Test unit marker functionality."""
    assert 1 + 1 == 2
