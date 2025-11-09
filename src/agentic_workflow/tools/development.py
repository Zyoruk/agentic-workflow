"""Development tools for agentic workflow system."""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.logging_config import get_logger
from . import Tool, ToolCapability

logger = get_logger(__name__)


class CodeAnalyzerTool(Tool):
    """Tool for analyzing Python code."""

    def __init__(self) -> None:
        capabilities = ToolCapability(
            name="code_analyzer",
            description="Analyze Python code for complexity, style, and potential issues",
            category="development",
            tags=["python", "analysis", "code-quality"],
            input_schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to analyze"},
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path for context",
                    },
                },
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "complexity": {"type": "number"},
                    "lines_of_code": {"type": "number"},
                    "functions": {"type": "array"},
                    "classes": {"type": "array"},
                    "issues": {"type": "array"},
                },
            },
        )
        super().__init__("code_analyzer", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute code analysis."""
        code = inputs["code"]
        file_path = inputs.get("file_path", "<string>")

        try:
            # Parse the code
            tree = ast.parse(code, filename=file_path)

            # Analyze structure
            functions = []
            classes = []
            issues = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": len(node.args.args),
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    classes.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "methods": len(
                                [n for n in node.body if isinstance(n, ast.FunctionDef)]
                            ),
                        }
                    )

            # Calculate metrics
            lines_of_code = len([line for line in code.split("\n") if line.strip()])
            complexity = len(functions) + len(classes) * 2  # Simple complexity metric

            # Basic issue detection
            if complexity > 20:
                issues.append("High complexity detected")
            if lines_of_code > 500:
                issues.append("File is quite large, consider splitting")

            return {
                "complexity": complexity,
                "lines_of_code": lines_of_code,
                "functions": functions,
                "classes": classes,
                "issues": issues,
                "success": True,
            }

        except SyntaxError as e:
            return {
                "complexity": 0,
                "lines_of_code": 0,
                "functions": [],
                "classes": [],
                "issues": [f"Syntax error: {e}"],
                "success": False,
            }

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return "code" in inputs and isinstance(inputs["code"], str)


class TestRunnerTool(Tool):
    """Tool for running tests."""

    def __init__(self) -> None:
        capabilities = ToolCapability(
            name="test_runner",
            description="Run Python tests and return results",
            category="development",
            tags=["testing", "python", "unittest", "pytest"],
            input_schema={
                "type": "object",
                "properties": {
                    "test_file": {"type": "string", "description": "Path to test file"},
                    "test_method": {
                        "type": "string",
                        "description": "Specific test method to run",
                    },
                    "framework": {
                        "type": "string",
                        "enum": ["pytest", "unittest"],
                        "default": "pytest",
                    },
                },
                "required": ["test_file"],
            },
        )
        super().__init__("test_runner", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute test runner."""
        test_file = inputs["test_file"]
        test_method = inputs.get("test_method")
        framework = inputs.get("framework", "pytest")

        try:
            # Build command
            if framework == "pytest":
                cmd = ["python", "-m", "pytest", test_file, "-v"]
                if test_method:
                    cmd.append(f"-k {test_method}")
            else:
                cmd = ["python", "-m", "unittest", test_file]
                if test_method:
                    cmd[-1] = f"{test_file}.{test_method}"

            # Run tests
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "framework": framework,
            }

        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 5 minutes",
                "success": False,
                "framework": framework,
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "framework": framework,
            }

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        if "test_file" not in inputs:
            return False

        test_file = inputs["test_file"]
        if not isinstance(test_file, str):
            return False

        # Check if file exists
        path = Path(test_file)
        return path.exists() and path.suffix == ".py"


class DependencyManagerTool(Tool):
    """Tool for managing Python dependencies."""

    def __init__(self):
        capabilities = ToolCapability(
            name="dependency_manager",
            description="Manage Python dependencies and virtual environments",
            category="development",
            tags=["pip", "dependencies", "python", "packages"],
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["install", "uninstall", "list", "check"],
                    },
                    "package": {"type": "string", "description": "Package name"},
                    "version": {"type": "string", "description": "Package version"},
                    "requirements_file": {
                        "type": "string",
                        "description": "Path to requirements file",
                    },
                },
                "required": ["action"],
            },
        )
        super().__init__("dependency_manager", capabilities)

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute dependency management."""
        action = inputs["action"]
        package = inputs.get("package")
        version = inputs.get("version")
        requirements_file = inputs.get("requirements_file")

        try:
            if action == "install":
                if requirements_file:
                    cmd = [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        requirements_file,
                    ]
                elif package:
                    pkg_spec = f"{package}=={version}" if version else package
                    cmd = [sys.executable, "-m", "pip", "install", pkg_spec]
                else:
                    return {
                        "success": False,
                        "error": "Package or requirements file required for install",
                    }

            elif action == "uninstall":
                if not package:
                    return {
                        "success": False,
                        "error": "Package name required for uninstall",
                    }
                cmd = [sys.executable, "-m", "pip", "uninstall", package, "-y"]

            elif action == "list":
                cmd = [sys.executable, "-m", "pip", "list"]

            elif action == "check":
                cmd = [sys.executable, "-m", "pip", "check"]

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "action": action,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "action": action}

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return "action" in inputs and inputs["action"] in [
            "install",
            "uninstall",
            "list",
            "check",
        ]


# Tool factory functions for discovery
def create_default_code_analyzer():
    """Create default code analyzer tool."""
    return CodeAnalyzerTool()


def create_default_test_runner():
    """Create default test runner tool."""
    return TestRunnerTool()


def create_default_dependency_manager():
    """Create default dependency manager tool."""
    return DependencyManagerTool()
