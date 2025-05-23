# Development Conventions

This document outlines the development conventions, standards, and best practices for the Agentic Workflow project.

## Table of Contents

- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Testing Standards](#testing-standards)
- [Documentation Standards](#documentation-standards)
- [File Organization](#file-organization)
- [Naming Conventions](#naming-conventions)
- [Version Management](#version-management)
- [Code Quality](#code-quality)

## Code Style

### Python Code Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with the following tools and configurations:

- **Line Length**: 88 characters (Black default)
- **Formatter**: [Black](https://black.readthedocs.io/)
- **Import Sorting**: [isort](https://pycqa.github.io/isort/)
- **Linting**: [Flake8](https://flake8.pycqa.org/)
- **Type Checking**: [MyPy](https://mypy.readthedocs.io/)

### Code Formatting Rules

```python
# Good: Function with type hints and docstring
def format_response(data: Any, status: str = "success") -> Dict[str, Any]:
    """Format a standard API response.

    Args:
        data: The response data
        status: Response status (default: "success")

    Returns:
        Formatted response dictionary
    """
    return {"status": status, "data": data}

# Good: Class with proper typing
class WorkflowEngine:
    """Main workflow execution engine."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config

    def execute(self, workflow: Workflow) -> WorkflowResult:
        """Execute a workflow and return results."""
        pass
```

### Import Organization

```python
# Standard library imports
import asyncio
import json
from typing import Any, Dict, List, Optional

# Third-party imports
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from agentic_workflow.core import Engine
from agentic_workflow.utils import helpers
```

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation.

### Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation changes | - |
| `style` | Code style changes (formatting, etc.) | - |
| `refactor` | Code refactoring | - |
| `perf` | Performance improvements | PATCH |
| `test` | Adding/updating tests | - |
| `build` | Build system changes | - |
| `ci` | CI/CD changes | - |
| `chore` | Maintenance tasks | - |
| `revert` | Revert previous commit | - |

### Breaking Changes

For breaking changes, add `!` after the type or include `BREAKING CHANGE:` in the footer:

```bash
# Breaking change with !
feat!: redesign API interface

# Breaking change with footer
feat(api): add new authentication
BREAKING CHANGE: API now requires authentication headers
```

### Examples

```bash
# Feature additions
git commit -m "feat(core): implement workflow execution engine"
git commit -m "feat(api): add REST endpoint for workflow creation"

# Bug fixes
git commit -m "fix(core): handle edge case in workflow validation"
git commit -m "fix(api): resolve 500 error in authentication"

# Documentation
git commit -m "docs: add development setup instructions"
git commit -m "docs(api): update endpoint documentation"

# Testing
git commit -m "test(core): add unit tests for workflow engine"
git commit -m "test: increase coverage for utils module"
```

## Testing Standards

### Test Structure

```python
"""Test module for workflow engine."""
import pytest
from unittest.mock import Mock, patch

from agentic_workflow.core import WorkflowEngine


class TestWorkflowEngine:
    """Test cases for WorkflowEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = WorkflowEngine({"test": True})

    def test_execute_simple_workflow(self):
        """Test execution of a simple workflow."""
        # Arrange
        workflow = Mock()

        # Act
        result = self.engine.execute(workflow)

        # Assert
        assert result.success is True
```

### Test Categories

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **System Tests**: End-to-end testing

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_unit_functionality():
    """Unit test example."""
    pass

@pytest.mark.integration
def test_integration_functionality():
    """Integration test example."""
    pass

@pytest.mark.slow
def test_slow_functionality():
    """Slow test that can be skipped."""
    pass
```

### Coverage Requirements

- **Minimum Coverage**: 80%
- **Target Coverage**: 90%+
- **Critical Modules**: 95%+

## Documentation Standards

### Docstring Format

We use [Google Style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) docstrings:

```python
def complex_function(arg1: str, arg2: int, arg3: bool = False) -> Dict[str, Any]:
    """One line summary of the function.

    Longer description if needed. Can span multiple lines and include
    detailed explanations of the function's behavior.

    Args:
        arg1: Description of the first argument.
        arg2: Description of the second argument.
        arg3: Description of the optional third argument. Defaults to False.

    Returns:
        Dictionary containing the processed results with keys:
        - 'status': Processing status
        - 'data': Processed data

    Raises:
        ValueError: If arg1 is empty.
        TypeError: If arg2 is not an integer.

    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['status'])
        'success'
    """
    pass
```

### README Structure

Each module should have a README with:

- Purpose and scope
- Installation instructions
- Usage examples
- API reference
- Contributing guidelines

## File Organization

### Project Structure

```
src/agentic_workflow/
├── __init__.py              # Package initialization
├── core/                    # Core functionality
│   ├── __init__.py
│   ├── engine.py           # Main workflow engine
│   └── models.py           # Core data models
├── agents/                  # Agent implementations
├── api/                     # API endpoints
├── graph/                   # Graph processing
└── utils/                   # Utility functions
    ├── __init__.py
    └── helpers.py          # Helper functions
```

### Import Guidelines

```python
# Relative imports within package
from .models import Workflow
from ..utils import helpers

# Absolute imports for external packages
from agentic_workflow.core import Engine
```

## Naming Conventions

### Python Naming

- **Variables**: `snake_case`
- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules**: `snake_case`
- **Packages**: `lowercase`

```python
# Variables and functions
user_name = "john_doe"
workflow_result = execute_workflow()

# Classes
class WorkflowEngine:
    pass

# Constants
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# Private attributes
class MyClass:
    def __init__(self):
        self._private_attr = None
        self.__very_private = None
```

### File Naming

- **Python files**: `snake_case.py`
- **Test files**: `test_*.py`
- **Documentation**: `kebab-case.md`
- **Configuration**: `kebab-case.yaml`

## Version Management

### Semantic Versioning

We follow [SemVer](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process

```bash
# Check what version would be bumped
make version-bump-dry

# Create release (automatic versioning)
make release

# Manual version bump if needed
cz bump --increment MINOR
```

### Version Files

Version is automatically updated in:
- `src/agentic_workflow/__init__.py`
- `pyproject.toml`

## Code Quality

### Pre-commit Hooks

All commits are automatically checked for:

- Trailing whitespace
- File endings
- YAML syntax
- Large files
- Merge conflicts
- Debug statements
- Code formatting (Black)
- Import sorting (isort)
- Linting (Flake8)
- Type checking (MyPy)
- Commit message format

### Quality Commands

```bash
# Run all quality checks
make quality

# Individual checks
make format      # Format code
make lint        # Run linting
make test        # Run tests
make test-cov    # Run tests with coverage
```

### Code Review Guidelines

1. **Functionality**: Does the code work as intended?
2. **Readability**: Is the code easy to understand?
3. **Performance**: Are there any performance issues?
4. **Testing**: Are there adequate tests?
5. **Documentation**: Is the code properly documented?
6. **Security**: Are there any security concerns?

## IDE Configuration

### VS Code Settings

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### PyCharm Settings

- Code style: Black
- Import optimization: isort
- Type checking: MyPy
- Test runner: pytest

## Contributing Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feat/amazing-feature`)
3. **Follow** conventions in this document
4. **Write** tests for new functionality
5. **Commit** using conventional commit format
6. **Push** to your branch
7. **Create** a Pull Request

## Resources

- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)

---

**Note**: These conventions are enforced by automated tools and pre-commit hooks. All contributions must adhere to these standards.
