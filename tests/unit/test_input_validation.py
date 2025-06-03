"""Unit tests for InputValidator and validation logic."""

import pytest

from agentic_workflow.guardrails.input_validation import (
    InputValidator,
    ValidationError,
    ValidationRule,
)


def test_register_and_validate_rule():
    validator = InputValidator(strict_mode=True)
    rule = ValidationRule(
        name="age", validator=lambda v: v > 18, error_message="Must be > 18"
    )
    validator.add_rule(rule.name, rule)
    # Passes
    data = {"age": 21}
    result = validator.validate("age", data["age"], ["age"])
    assert result is True
    # Fails
    data = {"age": 10}
    with pytest.raises(ValidationError):
        validator.validate("age", data["age"], ["age"])


def test_validate_multiple_rules():
    validator = InputValidator(strict_mode=True)
    rule1 = ValidationRule(name="x", validator=lambda v: v > 0, error_message="x>0")
    rule2 = ValidationRule(name="y", validator=lambda v: v < 10, error_message="y<10")
    validator.add_rule(rule1.name, rule1)
    validator.add_rule(rule2.name, rule2)
    # Both pass
    data = {"x": 1, "y": 5}
    result_x = validator.validate("x", data["x"], ["x"])
    result_y = validator.validate("y", data["y"], ["y"])
    assert result_x is True
    assert result_y is True
    # One fails
    data = {"x": -1, "y": 5}
    with pytest.raises(ValidationError):
        validator.validate("x", data["x"], ["x"])
    # Both fail
    data = {"x": -1, "y": 20}
    with pytest.raises(ValidationError):
        validator.validate("x", data["x"], ["x"])
    with pytest.raises(ValidationError):
        validator.validate("y", data["y"], ["y"])


def test_validate_missing_field():
    validator = InputValidator(strict_mode=True)
    rule = ValidationRule(
        name="foo", validator=lambda v: v == 1, error_message="foo==1"
    )
    validator.add_rule(rule.name, rule)
    data = {"bar": 1}
    with pytest.raises(ValidationError):
        validator.validate("foo", data.get("foo"), ["foo"])


def test_non_strict_mode():
    validator = InputValidator(strict_mode=False)
    rule = ValidationRule(
        name="foo", validator=lambda v: v == 1, error_message="foo==1"
    )
    validator.add_rule(rule.name, rule)
    # Test with missing field
    data = {"bar": 1}
    result = validator.validate("foo", data.get("foo"), ["foo"])
    assert result is False  # Should return False when field is missing
    # Test with field present but invalid
    data = {"foo": 2}
    result = validator.validate("foo", data["foo"], ["foo"])
    assert result is False  # Should return False when validation fails
    # Test with field present and valid
    data = {"foo": 1}
    result = validator.validate("foo", data["foo"], ["foo"])
    assert result is True  # Should return True when validation passes


def test_clear_rules():
    validator = InputValidator()
    rule = ValidationRule(name="foo", validator=lambda v: True, error_message="ok")
    validator.add_rule(rule.name, rule)
    assert "foo" in validator.rules
    del validator.rules["foo"]
    assert "foo" not in validator.rules
