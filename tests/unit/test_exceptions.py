import pytest

from agentic_workflow.core import exceptions


@pytest.mark.unit
def test_custom_exception_str():
    err = exceptions.AgenticWorkflowError("fail")
    assert str(err) == "fail"


@pytest.mark.unit
def test_specific_exceptions():
    with pytest.raises(exceptions.ConfigurationError):
        raise exceptions.ConfigurationError("bad config")
