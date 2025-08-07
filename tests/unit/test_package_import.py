import importlib

import pytest


@pytest.mark.unit
def test_import_package_without_optional_dependencies():
    module = importlib.import_module("agentic_workflow")
    assert module is not None
