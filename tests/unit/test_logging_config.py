import pytest

from agentic_workflow.core import logging_config


@pytest.mark.unit
def test_get_logger_returns_logger():
    logger = logging_config.get_logger("test_logger")
    assert logger.name == "test_logger"
    logger.info("This is a test log message.")
