# Agentic Workflow System

> AI-driven autonomous software development workflow system

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

An advanced agentic workflow system that enables autonomous software development through AI-driven agents, comprehensive planning, and self-improving processes.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [💻 Development Setup](#-development-setup)
- [🔧 Development Workflow](#-development-workflow)
- [🧪 Testing](#-testing)
- [📝 Documentation](#-documentation)
- [🔄 Version Management](#-version-management)
- [📊 Code Quality](#-code-quality)
- [🤝 Contributing](#-contributing)
- [📚 Project Structure](#-project-structure)

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Git**
- **Conda or venv** (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-workflow.git
cd agentic-workflow

# Create and activate environment
conda create -n agentic-workflow python=3.11 -y
conda activate agentic-workflow

# Install the package in development mode
pip install -e ".[dev,docs,test]"

# Set up pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Verify installation
make package-check
```

## 💻 Development Setup

### Environment Setup

The project uses **conda** for environment management and **pip** for package installation:

```bash
# Create environment
conda create -n agentic-workflow python=3.11

# Activate environment
conda activate agentic-workflow

# Install all dependencies
make install

# Set up development environment
make dev-setup
```

### Available Make Commands

```bash
# Show all available commands
make help

# Development
make install        # Install package and dependencies
make dev-setup      # Complete development environment setup

# Code Quality
make format         # Format code with Black and isort
make lint           # Run linting (Flake8 + MyPy)
make quality        # Run all quality checks
make format-check   # Check if code is properly formatted

# Testing
make test           # Run all tests
make test-cov       # Run tests with coverage report
make test-unit      # Run only unit tests
make test-integration  # Run only integration tests
make test-fast      # Run tests excluding slow ones

# Version Management
make version-check     # Check current version
make version-bump-dry  # Preview version bump
make version-bump      # Bump version based on commits
make changelog         # Generate/update CHANGELOG.md
make release          # Create release (bump + changelog + tag)
make commit           # Interactive conventional commit

# Utilities
make clean            # Clean build artifacts
make package-check    # Verify package can be imported
```

### IDE Configuration

#### VS Code (Recommended)

Create `.vscode/settings.json`:

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

## 🔧 Development Workflow

### 1. Daily Development

```bash
# Start development
conda activate agentic-workflow

# Create feature branch
git checkout -b feat/amazing-feature

# Make changes, then check quality
make quality

# Commit using conventional commits
git commit -m "feat(core): implement amazing feature"
# or use interactive commit
make commit
```

### 2. Code Quality Checks

All commits are automatically validated with **pre-commit hooks**:

- ✅ **Code Formatting** (Black, isort)
- ✅ **Linting** (Flake8, MyPy)
- ✅ **Commit Format** (Conventional Commits)
- ✅ **File Checks** (trailing whitespace, large files, etc.)

### 3. Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test categories
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-fast        # Skip slow tests
```

### 4. Release Process

```bash
# Check what version would be bumped
make version-bump-dry

# Create a release (automatic versioning)
make release

# Push to remote
git push origin main --tags
```

## 🧪 Testing

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_helpers.py
│   └── test_example.py
├── integration/       # Integration tests
│   └── test_example_integration.py
└── system/           # System tests (future)
```

### Writing Tests

```python
import pytest
from agentic_workflow.utils.helpers import format_response

@pytest.mark.unit
def test_format_response():
    """Test response formatting."""
    result = format_response({"key": "value"})
    assert result["status"] == "success"
    assert result["data"] == {"key": "value"}
```

### Coverage Requirements

- **Minimum**: 80%
- **Target**: 90%+
- **Critical modules**: 95%+

## 📝 Documentation

### Project Documentation

- **[CONVENTIONS.md](CONVENTIONS.md)** - Development conventions and standards
- **[CHANGELOG.md](CHANGELOG.md)** - Automated changelog
- **[docs/](docs/)** - Comprehensive project documentation

### Code Documentation

We use **Google-style docstrings**:

```python
def complex_function(arg1: str, arg2: int) -> Dict[str, Any]:
    """One line summary of the function.

    Args:
        arg1: Description of the first argument.
        arg2: Description of the second argument.

    Returns:
        Dictionary containing the processed results.

    Raises:
        ValueError: If arg1 is empty.
    """
    pass
```

## 🔄 Version Management

We use **automated semantic versioning** with [Commitizen](https://commitizen-tools.github.io/commitizen/):

### Conventional Commits

```bash
# Features (MINOR version bump)
git commit -m "feat(core): add new workflow engine"

# Bug fixes (PATCH version bump)
git commit -m "fix(api): resolve authentication issue"

# Breaking changes (MAJOR version bump)
git commit -m "feat!: redesign API interface"
git commit -m "feat(api): add auth\n\nBREAKING CHANGE: requires new headers"
```

### Release Workflow

1. **Develop** using conventional commits
2. **Test** thoroughly (`make quality`)
3. **Release** automatically (`make release`)
4. **Deploy** (manual or CI/CD)

## 📊 Code Quality

### Automated Quality Assurance

- 🔧 **Black** - Code formatting
- 📦 **isort** - Import organization
- 🔍 **Flake8** - Linting and style
- 🏷️ **MyPy** - Type checking
- ✅ **pytest** - Testing framework
- 📈 **Coverage** - Test coverage measurement
- 🪝 **Pre-commit** - Automated quality checks

### Quality Standards

- **Code Style**: PEP 8 + Black (88 char line length)
- **Type Hints**: Required for all public APIs
- **Test Coverage**: Minimum 80%
- **Documentation**: Google-style docstrings required

## 🤝 Contributing

We welcome contributions! Please follow our development conventions:

### Quick Contributing Guide

1. **Read** [CONVENTIONS.md](CONVENTIONS.md) for detailed standards
2. **Fork** the repository
3. **Create** a feature branch (`git checkout -b feat/amazing-feature`)
4. **Follow** our coding conventions
5. **Write** tests for new functionality
6. **Commit** using conventional commit format
7. **Ensure** all quality checks pass (`make quality`)
8. **Push** to your branch
9. **Create** a Pull Request

### Development Conventions

For detailed development standards, see **[CONVENTIONS.md](CONVENTIONS.md)**:

- 🎨 **Code Style** - Python formatting and organization
- 📝 **Commit Format** - Conventional commits specification
- 🧪 **Testing Standards** - Test structure and requirements
- 📚 **Documentation** - Docstring and README standards
- 🗂️ **File Organization** - Project structure guidelines
- 🏷️ **Naming Conventions** - Variable, function, and file naming
- 🔄 **Version Management** - Semantic versioning process
- ✅ **Code Quality** - Automated quality assurance

## 📚 Project Structure

```
agentic-workflow/
├── .github/                    # GitHub workflows and templates
├── docs/                       # Project documentation
│   ├── architecture/          # Architecture documentation
│   ├── implementation/        # Implementation guides
│   ├── planning/              # Project planning
│   └── requirements/          # Requirements specification
├── src/agentic_workflow/      # Main Python package
│   ├── __init__.py           # Package initialization
│   ├── core/                 # Core workflow functionality
│   ├── agents/               # AI agent implementations
│   ├── api/                  # REST API endpoints
│   ├── graph/                # Graph processing
│   └── utils/                # Utility functions
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── system/               # System tests
├── tools/                     # Development tools
│   ├── scripts/              # Utility scripts
│   └── config/               # Tool configurations
├── .pre-commit-config.yaml    # Pre-commit hooks
├── pyproject.toml            # Project configuration
├── Makefile                  # Development commands
├── CONVENTIONS.md            # Development conventions
├── CHANGELOG.md              # Automated changelog
└── README.md                 # This file
```

### Key Components

- **Core Engine**: Workflow execution and management
- **AI Agents**: LangChain-based intelligent agents
- **Graph Processing**: NetworkX-based workflow graphs
- **API Layer**: FastAPI REST endpoints
- **Memory Management**: Neo4j and Weaviate integration
- **Monitoring**: Prometheus metrics and logging

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [docs/](docs/)
- **Conventions**: [CONVENTIONS.md](CONVENTIONS.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/agentic-workflow/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/agentic-workflow/discussions)

---

**🚀 Ready to contribute?** Start by reading our [development conventions](CONVENTIONS.md) and running `make dev-setup`!

## Features

- Core engine for workflow management
- Agent-based task execution
- Flexible memory system
  - Short-term memory
  - Vector store (Weaviate) for long-term memory
  - Cache system
  - LangChain integration for embeddings
- Plugin architecture
- Robust event system
- Extensible service components

## Installation

```bash
# Basic installation
pip install agentic-workflow

# With development dependencies
pip install agentic-workflow[dev]

# With embedding support (for LangChain integration)
pip install agentic-workflow[embedding]
```
