"""Safety check protocols for the agentic workflow system."""

import re
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SafetyLevel(Enum):
    """Safety levels for checks."""

    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class SafetyViolation:
    """Represents a safety rule violation."""

    def __init__(
        self,
        rule_id: str,
        description: str,
        level: SafetyLevel = SafetyLevel.VIOLATION,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize safety violation.

        Args:
        rule_id: ID of the violated rule
        description: Description of the violation
        level: Severity level
        context: Additional context information
        """
        self.rule_id = rule_id
        self.description = description
        self.level = level
        self.context = context or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
        Dictionary representation
        """
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "level": self.level.value,
            "context": self.context,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        """Get string representation.

        Returns:
        String representation
        """
        return f"[{self.level.value.upper()}] Rule {self.rule_id}: {self.description}"


class SafetyChecker:
    """Safety check system for enforcing safety protocols."""

    def __init__(self) -> None:
        """Initialize safety checker."""
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.violations: List[SafetyViolation] = []
        self.violation_handlers: Dict[SafetyLevel, List[Callable]] = {}

        # Initialize default safety rules
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default safety rules."""
        # Content safety rules
        self.add_rule(
            rule_id="content_harmful_keywords",
            check_func=self._check_harmful_keywords,
            description="Check for harmful content keywords",
            level=SafetyLevel.VIOLATION,
            enabled=True,
            config={
                "keywords": [
                    "hack",
                    "exploit",
                    "attack",
                    "illegal",
                    "malware",
                    "vulnerability",
                    "bypass",
                    "steal",
                    "destroy",
                ]
            },
        )

        # Code safety rules
        self.add_rule(
            rule_id="code_dangerous_imports",
            check_func=self._check_dangerous_imports,
            description="Check for dangerous code imports",
            level=SafetyLevel.VIOLATION,
            enabled=True,
            config={
                "patterns": [
                    r"import\s+os(?:\s|\.)|from\s+os\s+import",
                    r"import\s+sys(?:\s|\.)|from\s+sys\s+import",
                    r"import\s+subprocess(?:\s|\.)|from\s+subprocess\s+import",
                    r"import\s+shutil(?:\s|\.)|from\s+shutil\s+import",
                ]
            },
        )

        # System safety rules
        self.add_rule(
            rule_id="system_file_access",
            check_func=self._check_file_access,
            description="Check for unsafe file access",
            level=SafetyLevel.VIOLATION,
            enabled=True,
            config={
                "restricted_paths": [
                    "/etc",
                    "/var",
                    "/usr",
                    "/bin",
                    "/sbin",
                    "C:\\Windows",
                    "C:\\Program Files",
                ]
            },
        )

    def add_rule(
        self,
        rule_id: str,
        check_func: Callable,
        description: str,
        level: SafetyLevel = SafetyLevel.VIOLATION,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a safety rule.

        Args:
        rule_id: Unique rule identifier
        check_func: Function that implements the check
        description: Rule description
        level: Violation severity level
        enabled: Whether the rule is enabled
        config: Rule configuration
        """
        self.rules[rule_id] = {
            "check_func": check_func,
            "description": description,
            "level": level,
            "enabled": enabled,
            "config": config or {},
        }
        logger.debug(f"Added safety rule: {rule_id}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a safety rule.

        Args:
        rule_id: Rule identifier

        Returns:
        True if rule was removed, False otherwise
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"Removed safety rule: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a safety rule.

        Args:
        rule_id: Rule identifier

        Returns:
        True if rule was enabled, False otherwise
        """
        if rule_id in self.rules:
            self.rules[rule_id]["enabled"] = True
            logger.debug(f"Enabled safety rule: {rule_id}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a safety rule.

        Args:
        rule_id: Rule identifier

        Returns:
        True if rule was disabled, False otherwise
        """
        if rule_id in self.rules:
            self.rules[rule_id]["enabled"] = False
            logger.debug(f"Disabled safety rule: {rule_id}")
            return True
        return False

    def update_rule_config(self, rule_id: str, config: Dict[str, Any]) -> bool:
        """Update rule configuration.

        Args:
        rule_id: Rule identifier
        config: New configuration

        Returns:
        True if config was updated, False otherwise
        """
        if rule_id in self.rules:
            self.rules[rule_id]["config"].update(config)
            logger.debug(f"Updated config for rule: {rule_id}")
            return True
        return False

    def register_violation_handler(
        self, level: SafetyLevel, handler: Callable[[SafetyViolation], None]
    ) -> None:
        """Register a handler for safety violations.

        Args:
        level: Violation level
        handler: Handler function
        """
        if level not in self.violation_handlers:
            self.violation_handlers[level] = []

        self.violation_handlers[level].append(handler)
        logger.debug(f"Registered violation handler for level: {level.value}")

    def check_safety(
        self, data: Any, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[SafetyViolation]]:
        """Check data against all enabled safety rules.

        Args:
        data: Data to check
        context: Additional context

        Returns:
        Tuple of (is_safe, violations)
        """
        context = context or {}
        self.violations = []

        for rule_id, rule in self.rules.items():
            if not rule["enabled"]:
                continue

            try:
                check_func = rule["check_func"]
                level = rule["level"]
                config = rule["config"]

                # Run the check
                result = check_func(data, config, context)

                if not result["is_safe"]:
                    violation = SafetyViolation(
                        rule_id=rule_id,
                        description=result.get("description", rule["description"]),
                        level=level,
                        context=result.get("context", {}),
                    )

                    self.violations.append(violation)
                    self._handle_violation(violation)

                    logger.warning(f"Safety violation: {violation}")

            except Exception as e:
                logger.error(f"Error in safety check {rule_id}: {e}")

        # Determine overall safety
        critical_violations = any(
            v.level == SafetyLevel.CRITICAL for v in self.violations
        )
        is_safe = len(self.violations) == 0 or (
            not critical_violations and context.get("allow_warnings", False)
        )

        return is_safe, self.violations

    def _handle_violation(self, violation: SafetyViolation) -> None:
        """Handle a safety violation by calling registered handlers.

        Args:
        violation: Safety violation
        """
        # Call handlers for this level
        if violation.level in self.violation_handlers:
            for handler in self.violation_handlers[violation.level]:
                try:
                    handler(violation)
                except Exception as e:
                    logger.error(f"Error in violation handler: {e}")

        # Always call handlers for any level
        if SafetyLevel.INFO in self.violation_handlers:
            for handler in self.violation_handlers[SafetyLevel.INFO]:
                try:
                    handler(violation)
                except Exception as e:
                    logger.error(f"Error in general violation handler: {e}")

    def get_violations(
        self, level: Optional[SafetyLevel] = None
    ) -> List[SafetyViolation]:
        """Get safety violations.

        Args:
        level: Optional filter by level

        Returns:
        List of violations
        """
        if level:
            return [v for v in self.violations if v.level == level]
        return self.violations

    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self.violations = []

    # Default safety check implementations

    def _check_harmful_keywords(
        self, data: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for harmful content keywords.

        Args:
        data: String data to check
        config: Rule configuration
        context: Additional context

        Returns:
        Check result
        """
        # Non-string data is safe
        if not isinstance(data, str):
            return {"is_safe": True}

        keywords = config.get("keywords", [])
        found_keywords = []

        # Check for harmful keywords
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, data, re.IGNORECASE):
                found_keywords.append(keyword)

        # Return result based on findings
        if found_keywords:
            return {
                "is_safe": False,
                "description": f"Harmful keywords detected: {', '.join(found_keywords)}",
                "context": {"keywords": found_keywords},
            }
        else:
            # No harmful keywords found
            return {"is_safe": True}

    def _check_dangerous_imports(
        self, data: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for dangerous code imports.

        Args:
        data: Code to check
        config: Rule configuration
        context: Additional context

        Returns:
        Check result
        """
        # Non-string data is safe
        if not isinstance(data, str):
            return {"is_safe": True}

        patterns = config.get("patterns", [])
        found_patterns = []

        # Check for dangerous import patterns
        for pattern in patterns:
            if re.search(pattern, data, re.MULTILINE):
                found_patterns.append(pattern)

        # If dangerous imports found and not allowed in context
        if found_patterns and not context.get("allow_system_imports", False):
            return {
                "is_safe": False,
                "description": "Dangerous imports detected",
                "context": {"patterns": found_patterns},
            }
        else:
            # No dangerous imports or they are allowed
            return {"is_safe": True}

    def _check_file_access(
        self, data: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for unsafe file access.

        Args:
        data: Path or command to check
        config: Rule configuration
        context: Additional context

        Returns:
        Check result
        """
        # Non-string data is safe
        if not isinstance(data, str):
            return {"is_safe": True}

        restricted_paths = config.get("restricted_paths", [])
        matched_path = None

        # Find first restricted path match
        for path in restricted_paths:
            if path in data:
                matched_path = path
                break

        # Return result based on findings
        if matched_path:
            return {
                "is_safe": False,
                "description": f"Restricted path access detected: {matched_path}",
                "context": {"path": matched_path},
            }
        else:
            # No restricted paths found
            return {"is_safe": True}

    def check_multiple(
        self, items: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check multiple data items for safety.

        Args:
        items: Dictionary of named data items
        context: Additional context

        Returns:
        Dictionary with check results
        """
        context = context or {}
        results = {}
        all_safe = True
        all_violations = []

        for name, data in items.items():
            item_context = context.copy()
            item_context["item_name"] = name

            is_safe, violations = self.check_safety(data, item_context)
            results[name] = {
                "is_safe": is_safe,
                "violations": [v.to_dict() for v in violations],
            }

            all_safe = all_safe and is_safe
            all_violations.extend(violations)

        return {
            "all_safe": all_safe,
            "item_results": results,
            "violations": [v.to_dict() for v in all_violations],
        }
