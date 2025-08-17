# Agentic Workflow System - GitHub Copilot Instructions

**ALWAYS follow these instructions first. Only fallback to additional search and context gathering if the information provided here is incomplete or found to be in error.**

## Working Effectively

### Bootstrap and Environment Setup
- **Environment**: Python 3.12+ (tested with 3.12.3), pip available
- **Minimal setup that works reliably**:
  ```bash
  # 1. Minimal package installation (1-2 minutes)
  make install-minimal
  
  # 2. Install development tools manually (network limitations in some environments)
  pip install pytest black flake8 mypy isort pytest-asyncio pytest-mock pytest-cov
  
  # 3. For documentation work
  pip install sphinx sphinx-rtd-theme mkdocs mkdocs-material
  
  # 4. Verify installation
  make package-check
  ```

- **Full installation may fail** due to network timeouts in sandboxed environments:
  ```bash
  # This command may timeout - use minimal approach above instead
  make install  # fails with network timeouts - use manual approach
  ```

### Build and Test Commands (NEVER CANCEL)
- **CRITICAL**: Set timeout to 120+ seconds for all commands. Build times are fast but may take longer in some environments.

#### Core Development Commands
```bash
# Testing - takes 4-5 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
make test-unit          # Run unit tests (115 tests, ~4 seconds)
make test              # May fail without full dev dependencies

# Code Quality - takes 3-7 seconds each. NEVER CANCEL. Set timeout to 60+ seconds.  
make format            # Format with Black and isort (~7 seconds)
make lint              # Flake8 and MyPy linting (~3 seconds) - will show formatting issues
make format-check      # Check formatting without changes

# Documentation - takes <1 second. NEVER CANCEL. Set timeout to 30+ seconds.
make docs-init         # Initialize Sphinx docs structure (~0.4 seconds)
```

#### Package Management
```bash
# Installation verification
make package-check     # Verify package imports correctly

# Cleanup
make clean            # Clean build artifacts
```

## Validation Scenarios

### ALWAYS test these scenarios after making changes:

#### 1. Basic Package Import Test
```bash
python -c "
from agentic_workflow.core.reasoning import ReasoningEngine
print('🧠 Testing reasoning engine...')
engine = ReasoningEngine(agent_id='test_agent')
print('✅ Reasoning engine created successfully!')

print('📁 Testing package structure...')
import agentic_workflow.agents
import agentic_workflow.core  
import agentic_workflow.tools
print('✅ All core modules imported successfully!')

print('🔧 Testing tool system...')
from agentic_workflow.tools import ToolManager
print('✅ Tool manager imported successfully!')
"
```
Expected: Should print success messages without errors.

#### 2. Core Workflow Validation
```bash
# Test unit tests to ensure core functionality
make test-unit
```
Expected: 115 tests pass in ~4 seconds with some warnings (normal).

#### 3. Code Quality Validation  
```bash
# Format code first, then check linting
make format
make lint
```
Expected: Formatting may change files. Linting may show issues that need manual fixes (trailing whitespace, unused imports).

## EXACT Commands for Common Tasks

### Development Workflow
```bash
# 1. Start development
make install-minimal
pip install pytest black flake8 mypy isort pytest-asyncio pytest-mock pytest-cov

# 2. Make changes, then validate
make format              # NEVER CANCEL: ~7 seconds
make lint               # NEVER CANCEL: ~3 seconds, may show issues
make test-unit          # NEVER CANCEL: ~4 seconds

# 3. Manual validation  
python -c "import agentic_workflow; print(f'✅ Package {agentic_workflow.__version__} imported successfully!')"

# 4. Clean up before commit
make format            # Fix any remaining format issues manually if lint shows problems
```

### Documentation Work
```bash
# Initialize documentation
make docs-init         # NEVER CANCEL: ~0.4 seconds

# For documentation dependencies  
pip install sphinx sphinx-rtd-theme mkdocs mkdocs-material
```

## Key Projects in Codebase

### Core Architecture (`src/agentic_workflow/`)
- **`core/`** - Main workflow engine, reasoning patterns (Chain of Thought, ReAct, RAISE), communication system
- **`agents/`** - AI agent implementations (planning, code generation, CI/CD, testing, review)
- **`tools/`** - Tool integration system with discovery, registry, and execution
- **`memory/`** - Memory management (Redis, Weaviate, Neo4j integration)
- **`mcp/`** - Model Context Protocol integration for external tool support
- **`api/`** - FastAPI REST endpoints
- **`monitoring/`** - Prometheus metrics and health checks

### Testing Structure (`tests/`)
- **`unit/`** - Unit tests (115 tests, ~4 seconds to run)
- **`integration/`** - Integration tests (may require external services)

### Configuration Files
- **`pyproject.toml`** - Modern Python packaging, dependencies, tool configuration
- **`Makefile`** - Development automation (run `make help` for all commands)
- **`.pre-commit-config.yaml`** - Code quality hooks (requires manual tool installation)

## Common Issues and Solutions

### Network/Installation Issues
- **Issue**: `make install` fails with timeout
- **Solution**: Use `make install-minimal` + manual tool installation approach shown above

### Linting Issues  
- **Issue**: `make lint` shows trailing whitespace, unused imports
- **Solution**: Run `make format` first, then manually fix remaining issues in editor

### Missing Dependencies
- **Issue**: `No module named 'pytest_asyncio'` or similar
- **Solution**: Install manually: `pip install pytest-asyncio pytest-mock pytest-cov`

### Import Errors
- **Issue**: Cannot import agentic_workflow modules
- **Solution**: Ensure `make package-check` passes and package is installed in editable mode

## Repository Structure Quick Reference

```
agentic-workflow/
├── src/agentic_workflow/          # Main Python package  
│   ├── core/                      # Core reasoning, communication, config
│   ├── agents/                    # AI agents (planning, code gen, CI/CD, etc.)
│   ├── tools/                     # Tool integration system
│   ├── memory/                    # Memory management (Redis, Weaviate, Neo4j)
│   ├── mcp/                       # Model Context Protocol integration
│   ├── api/                       # FastAPI REST endpoints
│   └── monitoring/                # Metrics and health checks
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests (115 tests, ~4 seconds)
│   └── integration/               # Integration tests
├── docs/                          # Documentation
├── Makefile                       # Development commands  
├── pyproject.toml                 # Python packaging and tool config
└── README.md                      # Project overview
```

## Timeout Values and Timing Expectations

**CRITICAL**: Always use these timeout values to prevent premature cancellation:

| Command | Expected Time | Minimum Timeout | Notes |
|---------|--------------|-----------------|-------|
| `make install-minimal` | 1-2 minutes | 180 seconds | May vary by network |
| `make test-unit` | 4 seconds | 60 seconds | 115 tests, consistent timing |
| `make format` | 7 seconds | 60 seconds | Black + isort on all files |
| `make lint` | 3 seconds | 60 seconds | Flake8 + MyPy, may show issues |
| `make docs-init` | 0.4 seconds | 30 seconds | Very fast |
| `make package-check` | 2 seconds | 30 seconds | Import verification |

**NEVER CANCEL any build or test commands** - always wait for completion.

## CI/CD Pipeline Compatibility

Always run these commands before committing to ensure CI compatibility:
```bash
make format            # NEVER CANCEL: ~7 seconds
make lint             # NEVER CANCEL: ~3 seconds - fix issues manually  
make test-unit        # NEVER CANCEL: ~4 seconds
```

The codebase uses:
- **Black** (88 char line length) and **isort** for formatting
- **Flake8** and **MyPy** for linting and type checking  
- **pytest** with asyncio support for testing
- **Conventional commits** with Commitizen for version management