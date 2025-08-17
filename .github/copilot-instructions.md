# Agentic Workflow System - Copilot Instructions

**ALWAYS follow these instructions first and fallback to additional search and context gathering only if the information here is incomplete or found to be in error.**

## Working Effectively

### Bootstrap, Build, and Test the Repository

**CRITICAL**: Execute commands in this EXACT order. Do NOT skip steps or change the sequence.

```bash
# 1. Install minimal dependencies - WORKS RELIABLY
make install-minimal
# Expected time: 70 seconds. NEVER CANCEL - Set timeout to 120+ seconds.

# 2. Verify package installation
make package-check
# Expected time: 3 seconds. Should output: "✅ Package 0.6.0 imported successfully!"

# 3. Install additional testing tools (if needed)
pip install pytest pytest-cov pytest-asyncio pytest-mock coverage black isort flake8 mypy pre-commit commitizen
# Expected time: 30 seconds.

# 4. Run tests - CORE VALIDATION
python -m pytest tests/ -v
# Expected time: 9 seconds. NEVER CANCEL - Set timeout to 30+ seconds.
# Expected result: ~613 passed, ~9 failed (MCP integration failures expected without configuration)

# 5. Check code quality (will show current issues)
make format-check  # Shows formatting issues (expected to fail initially)
make lint         # Shows linting issues (expected to fail initially)
mypy src/         # Shows type checking issues (expected to fail initially)
```

### Full Development Installation (MAY FAIL)

**WARNING**: The full development installation frequently fails due to network timeouts:

```bash
# These commands MAY fail with network timeouts - document if they fail
make install      # FAILS: Network timeout to pypi.org
make install-dev  # FAILS: Network timeout to pypi.org  
make dev-setup    # FAILS: Network timeout to pypi.org
```

**If full installation fails**: Document it as "Installation fails due to firewall limitations. Use minimal installation workflow instead."

### Start Development Services

```bash
# Start API server (WORKS)
python -m uvicorn agentic_workflow.api.main:app --host 127.0.0.1 --port 8000
# Expected startup time: 3 seconds
# Health check URL: http://127.0.0.1:8000/api/v1/health (partially operational expected)
# Root API info: http://127.0.0.1:8000/

# Run basic examples (WORKS)
python examples/basic_workflow_example.py
# Expected time: 2 seconds, should complete successfully
```

## Validation

### Manual Testing Requirements

**ALWAYS run through these complete end-to-end scenarios after making changes:**

1. **Package Import Validation**:
   ```bash
   make package-check
   # Must output: "✅ Package 0.6.0 imported successfully!"
   ```

2. **Core Functionality Test**:
   ```bash
   python examples/basic_workflow_example.py
   # Must complete without errors and show workflow execution logs
   ```

3. **API Health Check**:
   ```bash
   # Start API in background
   python -m uvicorn agentic_workflow.api.main:app --host 127.0.0.1 --port 8000 &
   # Wait 5 seconds for startup
   curl -s http://127.0.0.1:8000/api/v1/health | python -m json.tool
   # Should return JSON with status "unhealthy" but with 4/6 checks passing
   # Kill the API process when done
   ```

4. **Test Suite Validation**:
   ```bash
   python -m pytest tests/ -v
   # Must pass at least 600+ tests with only MCP-related failures acceptable
   ```

### Build Time Expectations

**CRITICAL**: These are MEASURED timing expectations. Include NEVER CANCEL warnings:

- **`make install-minimal`**: 70 seconds. NEVER CANCEL. Set timeout to 120+ seconds.
- **`make package-check`**: 3 seconds
- **`python -m pytest tests/`**: 9 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
- **`make format-check`**: 5 seconds (will fail showing 35+ files need reformatting)
- **`make lint`**: 2 seconds (will fail showing many linting issues)
- **`mypy src/`**: 34 seconds. NEVER CANCEL. Set timeout to 60+ seconds. (will fail showing 258 type errors)
- **API startup**: 3 seconds
- **Example execution**: 2 seconds

## Development Workflow

### Daily Development Process

```bash
# 1. Start fresh (if needed)
make install-minimal  # NEVER CANCEL: 70 seconds

# 2. Verify current state
make package-check

# 3. Make your changes

# 4. Validate changes
python -m pytest tests/ -v  # NEVER CANCEL: 9 seconds

# 5. Test examples still work
python examples/basic_workflow_example.py

# 6. Check API still starts
python -m uvicorn agentic_workflow.api.main:app --host 127.0.0.1 --port 8000
# Test health endpoint: curl http://127.0.0.1:8000/api/v1/health
```

### Code Quality - Current State

**IMPORTANT**: The codebase currently has known quality issues that you should be aware of:

- **Formatting**: 35 files need Black formatting (`make format-check` fails)
- **Linting**: Many files have whitespace and import issues (`make lint` fails)  
- **Type checking**: 258 MyPy errors across 23 files (`mypy src/` fails)

**Before committing**: Always run the quality checks but expect them to fail initially:

```bash
make format-check  # Expected to fail - shows files needing formatting
make lint         # Expected to fail - shows linting issues  
mypy src/         # Expected to fail - shows type errors
```

### Installation Issues

**CRITICAL KNOWN ISSUE**: Network connectivity problems affect dependency installation:

- ✅ **`make install-minimal`** - WORKS (70 seconds)
- ❌ **`make install`** - FAILS with network timeout to pypi.org
- ❌ **`make install-dev`** - FAILS with network timeout to pypi.org
- ❌ **`make dev-setup`** - FAILS with network timeout to pypi.org

**Workaround**: Use individual pip install commands for specific tools:
```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock coverage
pip install black isort flake8 mypy
pip install pre-commit commitizen
```

## Repository Structure

### Key Directories
```
src/agentic_workflow/       # Main Python package
├── agents/                 # AI agent implementations  
├── api/                    # FastAPI REST endpoints
├── core/                   # Core workflow functionality
├── events/                 # Event system components
├── graph/                  # Neo4j graph processing
│   ├── application/        # Application layer
│   ├── domain/             # Domain models
│   └── infrastructure/     # Infrastructure layer
├── guardrails/             # Safety and validation guardrails
├── mcp/                    # Model Context Protocol integration
│   ├── client/             # MCP client implementation
│   ├── integration/        # MCP integration layer
│   └── tools/              # MCP tool implementations
├── memory/                 # Memory management (Redis, Weaviate)
│   └── connections/        # Memory connection handlers
├── monitoring/             # Prometheus metrics
├── tools/                  # Tool integration system
│   └── builtin/            # Built-in tool implementations
└── utils/                  # Utility functions

tests/                      # Test suite (622 tests total)
├── unit/                   # Unit tests (~613 pass)
│   ├── agents/             # Agent testing
│   ├── core/               # Core functionality tests
│   ├── graph/              # Graph processing tests
│   │   ├── application/    # Application layer tests
│   │   └── domain/         # Domain model tests
│   ├── mcp/                # MCP component tests
│   └── tools/              # Tool system tests
└── integration/            # Integration tests (~9 fail - MCP related)
    └── mcp/                # MCP integration tests

examples/                   # Working examples for testing
├── basic_workflow_example.py     # ✅ WORKS - Use for validation
├── reasoning_patterns_demo.py    # Reasoning system examples
├── tool_system_demo.py          # Tool integration examples
└── [15+ other examples]
```

### Important Files
- **`Makefile`** - All development commands (make help for full list)
- **`pyproject.toml`** - Project configuration and dependencies
- **`README.md`** - Comprehensive documentation
- **`CONVENTIONS.md`** - Development standards
- **`.pre-commit-config.yaml`** - Code quality hooks (requires setup)

## Common Tasks

### Available Make Commands (Validated)

```bash
# Installation (use minimal - others may fail)
make install-minimal    # ✅ WORKS (70s) - Core dependencies only
make install           # ❌ FAILS - Network timeout issues
make install-dev       # ❌ FAILS - Network timeout issues

# Testing  
make test              # ✅ WORKS (9s) - Runs pytest
make test-unit         # ✅ WORKS - Unit tests only
make test-integration  # ✅ WORKS - Integration tests only
make test-cov          # ✅ WORKS - With coverage report

# Code Quality (expect failures initially)
make format-check      # ❌ FAILS - 35 files need formatting
make lint              # ❌ FAILS - Many linting issues
make format            # Formats code with Black and isort
make quality           # Runs all quality checks

# Development
make package-check     # ✅ WORKS (3s) - Verify import
make clean             # ✅ WORKS - Clean build artifacts
make help              # ✅ WORKS - Show all commands
```

### Testing Strategy

**Test Categories**:
- **Unit tests**: `pytest -m unit` (fast, isolated)
- **Integration tests**: `pytest -m integration` (may require services)
- **Slow tests**: `pytest -m "not slow"` to skip time-consuming tests

**Coverage Requirements**:
- Minimum: 80%
- Target: 90%+
- Critical modules: 95%+

## Architecture Overview

### Core Components

1. **Workflow Engine** (`src/agentic_workflow/core/`)
   - Workflow execution and management
   - Component lifecycle management
   - Event system integration

2. **AI Agents** (`src/agentic_workflow/agents/`)
   - LangChain-based intelligent agents
   - Reasoning patterns (Chain of Thought, ReAct, RAISE)
   - Planning and execution capabilities

3. **Tool System** (`src/agentic_workflow/tools/`)
   - Dynamic tool discovery and registration
   - Built-in tool portfolio
   - Smart recommendations

4. **Memory Management** (`src/agentic_workflow/memory/`)
   - Redis for caching and short-term memory
   - Weaviate for vector storage
   - Neo4j for graph relationships

5. **API Layer** (`src/agentic_workflow/api/`)
   - FastAPI REST endpoints
   - Health monitoring
   - System status reporting

6. **Communication System** (`src/agentic_workflow/core/communication.py`)
   - Multi-agent communication
   - Message routing and filtering
   - RAISE pattern integration

### Monitoring and Health

- **Prometheus metrics**: Optional (disabled by default)
- **Health checks**: API endpoint `/api/v1/health`
- **Logging**: Configured via `agentic_workflow.core.logging_config`

## Environment Variables

### LLM Configuration (Optional)
```bash
export AGENTIC_LLM__OPENAI_API_KEY=sk-...
export AGENTIC_LLM__DEFAULT_MODEL=gpt-4o
export AGENTIC_LLM__USE_GPT5_PREVIEW=true
export AGENTIC_LLM__ENABLE_MODEL_HEALTH_CHECK=true
```

### Monitoring Configuration (Optional)
```bash
export AGENTIC_MONITORING__PROMETHEUS_ENABLED=true
export AGENTIC_MONITORING__PROMETHEUS_PORT=8000
```

## Troubleshooting

### Installation Issues
- **Network timeouts**: Use `make install-minimal` only
- **Missing dependencies**: Install individually with pip
- **Build failures**: Check Python version (requires 3.11+)

### Test Failures
- **9 MCP tests failing**: Expected without proper MCP configuration
- **613+ tests passing**: Normal and expected
- **RuntimeWarnings**: Expected for async mock issues

### API Issues  
- **Partially unhealthy status**: Normal without external services
- **4/6 health checks passing**: Expected in development environment
- **Memory/Communication failures**: Expected without Redis/Neo4j setup

## Quick Reference

### Essential Commands
```bash
make install-minimal    # Install core (70s, NEVER CANCEL)
make package-check      # Test import (3s)
python -m pytest tests/ -v  # Run tests (9s, NEVER CANCEL)
python examples/basic_workflow_example.py  # Test functionality
```

### Code Quality Commands
```bash
make format-check       # Check formatting (expect failures)
make lint              # Check linting (expect failures)
mypy src/              # Type checking (34s, expect failures)
```

### API Testing
```bash
python -m uvicorn agentic_workflow.api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/api/v1/health
```

Always validate changes using the complete testing scenarios above before considering work complete.