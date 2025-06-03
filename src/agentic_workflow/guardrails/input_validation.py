"""Input validation module for the agentic workflow system."""

import re
from typing import Any, Callable, Dict, List, Optional

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exception raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """Initialize validation error.

        Args:
        message: Error message
        field: Name of the field that failed validation
        value: Value that failed validation
        """
        self.field = field
        self.value = value
        super().__init__(message)


class ValidationRule:
    """Validation rule for input data."""

    def __init__(
        self,
        name: str,
        validator: Callable[[Any], bool],
        error_message: str = "Validation failed",
    ):
        """Initialize validation rule.

        Args:
        name: Rule name
        validator: Validation function
        error_message: Error message for validation failure
        """
        self.name = name
        self.validator = validator
        self.error_message = error_message

    def validate(self, value: Any) -> bool:
        """Validate value against rule.

        Args:
        value: Value to validate

        Returns:
        True if validation passed, False otherwise
        """
        try:
            return bool(self.validator(value))
        except Exception as e:
            logger.error(f"Validation rule {self.name} raised an exception: {e}")
            return False


class InputValidator:
    """Input validation for securing system inputs."""

    def __init__(self, strict_mode: bool = True) -> None:
        """Initialize input validator.

        Args:
        strict_mode: Whether to raise exceptions on validation failure
        """
        self.rules: Dict[str, List[ValidationRule]] = {}
        self.strict_mode = strict_mode
        self.validation_errors: List[ValidationError] = []

        # Create common validation rules
        self._create_common_rules()

    def _create_common_rules(self) -> None:
        """Create common validation rules."""
        # String validation
        self.add_rule(
            "non_empty_string",
            ValidationRule(
                name="non_empty_string",
                validator=lambda v: isinstance(v, str) and len(v.strip()) > 0,
                error_message="Value must be a non-empty string",
            ),
        )

        # Numeric validation
        self.add_rule(
            "positive_number",
            ValidationRule(
                name="positive_number",
                validator=lambda v: isinstance(v, (int, float)) and v > 0,
                error_message="Value must be a positive number",
            ),
        )

        # Email validation
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self.add_rule(
            "email",
            ValidationRule(
                name="email",
                validator=lambda v: isinstance(v, str) and bool(email_pattern.match(v)),
                error_message="Invalid email format",
            ),
        )

        # URL validation
        url_pattern = re.compile(
            r"^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
        )
        self.add_rule(
            "url",
            ValidationRule(
                name="url",
                validator=lambda v: isinstance(v, str) and bool(url_pattern.match(v)),
                error_message="Invalid URL format",
            ),
        )

        # Sanitization rules
        self.add_rule(
            "no_script_tags",
            ValidationRule(
                name="no_script_tags",
                validator=lambda v: isinstance(v, str) and "<script" not in v.lower(),
                error_message="Script tags are not allowed",
            ),
        )

    def add_rule(self, rule_id: str, rule: ValidationRule) -> None:
        """Add a validation rule.

        Args:
        rule_id: Unique identifier for the rule
        rule: Validation rule
        """
        if rule_id not in self.rules:
            self.rules[rule_id] = []
        self.rules[rule_id].append(rule)
        logger.debug(f"Added validation rule: {rule_id}")

    def validate(
        self, field: str, value: Any, rule_ids: Optional[List[str]] = None
    ) -> bool:
        """Validate a value against specified rules.

        Args:
        field: Field name
        value: Value to validate
        rule_ids: List of rule IDs to apply

        Returns:
        True if validation passed, False otherwise

        Raises:
        ValidationError: If validation fails and strict mode is enabled
        """
        # Reset errors for this validation
        self.validation_errors = []

        # If no rules specified, return True
        if not rule_ids:
            return True

        # Apply all rules
        for rule_id in rule_ids:
            if rule_id not in self.rules:
                logger.warning(f"Validation rule not found: {rule_id}")
                continue

            for rule in self.rules[rule_id]:
                if not rule.validate(value):
                    error = ValidationError(
                        message=rule.error_message, field=field, value=value
                    )
                    self.validation_errors.append(error)

                    logger.warning(
                        f"Validation failed: {field}={value}, rule={rule_id}, "
                        f"error={rule.error_message}"
                    )

                    if self.strict_mode:
                        raise error

                    return False

        return len(self.validation_errors) == 0

    def validate_dict(
        self, data: Dict[str, Any], rules_map: Dict[str, List[str]]
    ) -> bool:
        """Validate multiple fields in a dictionary.

        Args:
        data: Dictionary of field values
        rules_map: Mapping of field names to rule IDs

        Returns:
        True if all validations passed, False otherwise

        Raises:
        ValidationError: If validation fails and strict mode is enabled
        """
        all_valid = True

        for field, rule_ids in rules_map.items():
            if field not in data:
                logger.warning(f"Field not found in data: {field}")
                continue

            field_valid = self.validate(field, data[field], rule_ids)
            all_valid = all_valid and field_valid

            if not field_valid and self.strict_mode:
                return False

        return all_valid

    def sanitize_string(self, value: Any) -> str:
        """Sanitize a string input.

        Args:
        value: String to sanitize

        Returns:
        Sanitized string
        """
        # Convert non-string values to string
        sanitized_value = value
        if not isinstance(sanitized_value, str):
            sanitized_value = str(sanitized_value)

        # Remove potentially dangerous HTML
        sanitized = re.sub(
            r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
            "",
            sanitized_value,
            flags=re.IGNORECASE,
        )

        # Remove other potentially dangerous tags
        sanitized = re.sub(
            r"<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Escape HTML entities
        sanitized = (
            sanitized.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        return sanitized

    def get_errors(self) -> List[ValidationError]:
        """Get validation errors.

        Returns:
        List of validation errors
        """
        return self.validation_errors
