from typing import Any, Dict, cast

import pytest

from agentic_workflow.guardrails.safety_checks import SafetyChecker, SafetyLevel


@pytest.mark.unit
def test_add_and_remove_rule() -> None:
    checker = SafetyChecker()
    checker.add_rule(
        rule_id="test_rule",
        check_func=lambda d, c, ctx: {"is_safe": True},
        description="Test rule",
        level=SafetyLevel.WARNING,
        enabled=True,
        config={"foo": "bar"},
    )
    assert "test_rule" in checker.rules
    removed = checker.remove_rule("test_rule")
    assert removed is True
    assert "test_rule" not in checker.rules
    # Removing again returns False
    assert checker.remove_rule("test_rule") is False


@pytest.mark.unit
def test_check_dangerous_imports() -> None:
    checker = SafetyChecker()
    dangerous_code = "import os\nimport sys"
    config: Dict[str, Any] = {"patterns": [r"import os", r"import sys"]}
    context: Dict[str, bool] = {"allow_system_imports": False}
    result = checker._check_dangerous_imports(dangerous_code, config, context)
    assert not result["is_safe"]
    assert "patterns" in result["context"]
    # Allowed by context
    context = {"allow_system_imports": True}
    result = checker._check_dangerous_imports(dangerous_code, config, context)
    assert result["is_safe"]
    # Non-string data is always safe
    assert checker._check_dangerous_imports(cast(str, "123"), config, {})["is_safe"]


@pytest.mark.unit
def test_check_file_access() -> None:
    checker = SafetyChecker()
    config: Dict[str, Any] = {"restricted_paths": ["/etc", "/var"]}
    context: Dict[str, Any] = {}
    # Restricted path present
    result = checker._check_file_access("/etc/passwd", config, context)
    assert not result["is_safe"]
    assert "/etc" in result["description"]
    # No restricted path
    result = checker._check_file_access("/home/user/file.txt", config, context)
    assert result["is_safe"]
    # Non-string data is always safe
    assert checker._check_file_access(cast(str, "123"), config, {})["is_safe"]
