# Agentic Workflow Examples

This directory contains practical examples demonstrating various components and capabilities of the Agentic Workflow System.

## Core Agent Examples

### 🧮 Calculator Testing Demo

**Files:**
- `example_calculator.py` - Simple calculator module with functions and classes
- `test_agent_demo.py` - Comprehensive Testing Agent demonstration
- `test_generated_calculator.py` - Generated test file from the Testing Agent

**Description:**
Demonstrates the Testing Agent's capabilities including:
- **Test Generation**: Automatically generate unit and integration tests
- **Test Strategy Planning**: Create comprehensive testing strategies
- **Planning Capabilities**: Break down testing objectives into executable tasks
- **Code Analysis**: Analyze code structure and generate appropriate tests

**Usage:**
```bash
cd examples
python test_agent_demo.py
```

**What it demonstrates:**
1. **Unit Test Generation** - Generates comprehensive tests for calculator functions
2. **Integration Test Generation** - Creates integration tests for the Statistics class
3. **Test Strategy Creation** - Develops testing strategies with resource estimates
4. **Planning Workflow** - Shows how the agent can plan complex testing objectives
5. **Agent Capabilities** - Lists all available testing capabilities

### 🚀 CI/CD Deployment Demo

**Files:**
- `cicd_agent_demo.py` - Comprehensive CI/CD Agent demonstration

**Description:**
Demonstrates the CI/CD Agent's deployment automation capabilities including:
- **Pipeline Management**: Create and manage GitLab CI/CD pipelines
- **Deployment Automation**: Deploy applications to multiple environments
- **Environment Management**: Create, update, and monitor deployment environments
- **Health Monitoring**: Comprehensive system health and performance checks
- **Rollback Operations**: Automated rollback to previous stable versions
- **Production Workflows**: Enterprise-grade deployment with approval gates

**Usage:**
```bash
cd examples
python cicd_agent_demo.py
```

**What it demonstrates:**
1. **Pipeline Creation** - Generates GitLab CI YAML for Python and Kubernetes deployments
2. **Multi-Environment Deployment** - Deploys to development, staging, and production
3. **Environment Management** - Creates and monitors deployment environments
4. **Health Monitoring** - SSL, security, performance, and resource utilization checks
5. **Rollback Recovery** - Automated rollback with validation and logging
6. **Planning Intelligence** - Generates deployment plans with dependencies and estimates
7. **Production Safety** - Manual approval gates and comprehensive validation
8. **Resource Monitoring** - CPU, memory, disk usage, and response time tracking

### 📊 Generated Test Results

The demo generates actual runnable pytest tests that you can execute:

```bash
# Run the generated tests
pytest test_generated_calculator.py -v

# Check test coverage
pytest --cov=example_calculator test_generated_calculator.py

# Generate HTML coverage report
pytest --cov=example_calculator --cov-report=html test_generated_calculator.py
```

## System Component Examples

### 🧠 Memory System Examples

**Files:**
- `memory_system_example.py` - Basic memory operations demonstration
- `memory_service_example.py` - Advanced memory service features

**Description:**
Shows how to use the multi-store memory system with Redis, Weaviate, and graph storage.

### 🛡️ Guardrails Examples

**Files:**
- `guardrails_example.py` - Safety and validation system demonstration

**Description:**
Demonstrates input validation, safety checks, and error handling mechanisms.

### 🔄 Workflow Examples

**Files:**
- `basic_workflow_example.py` - Basic agent workflow orchestration

**Description:**
Shows how to coordinate multiple agents in a workflow.

## Running Examples

### Prerequisites

1. **Environment Setup:**
   ```bash
   conda activate agentic-workflow
   cd examples
   ```

2. **Required Services:**
   - Redis (for caching and short-term memory)
   - Weaviate (for vector storage - optional for basic demos)
   - OpenAI API key (for LLM features - optional for basic demos)

### Quick Start

```bash
# Run the Testing Agent demo (no external services required)
python test_agent_demo.py

# Run the CI/CD Agent demo (no external services required)
python cicd_agent_demo.py

# Run memory system examples (requires Redis)
python memory_system_example.py

# Run guardrails examples
python guardrails_example.py

# Run workflow orchestration examples
python basic_workflow_example.py
```

## Example Categories

| Category | Focus | Files | External Dependencies |
|----------|-------|-------|----------------------|
| **Testing** | Automated test generation and execution | `test_agent_demo.py`, `example_calculator.py` | None |
| **CI/CD** | Deployment automation and pipeline management | `cicd_agent_demo.py` | None |
| **Memory** | Multi-store memory operations | `memory_*.py` | Redis, Weaviate |
| **Safety** | Validation and error handling | `guardrails_example.py` | None |
| **Workflow** | Agent orchestration | `basic_workflow_example.py` | Redis |

## Learning Path

1. **Start with Testing Agent** - Shows core agent capabilities without external dependencies
2. **Explore CI/CD Agent** - Learn deployment automation and environment management
3. **Understand Memory System** - Learn about data persistence and retrieval
4. **Try Guardrails** - See how safety and validation work
5. **Experiment with Workflows** - Coordinate multiple agents

## Agent Capabilities Overview

### Testing Agent (Task 3.3) ✅
- Test generation (unit, integration, functional)
- Test execution and result analysis
- Coverage analysis and reporting
- Test strategy planning
- Test validation and quality assessment

### CI/CD Agent (Task 3.4) ✅
- GitLab CI/CD pipeline integration
- Multi-environment deployment automation
- Environment provisioning and management
- Health monitoring and validation
- Automated rollback and recovery
- Infrastructure as Code (IaC) support

## Contributing Examples

When adding new examples:

1. **Follow naming convention**: `{agent_name}_demo.py` or `{component}_example.py`
2. **Include comprehensive docstrings** explaining what the example demonstrates
3. **Add error handling** for graceful failure when services are unavailable
4. **Update this README** with example descriptions
5. **Include sample output** in comments or separate files

## Support

For questions about examples or to report issues:
- Check the main project documentation in `/docs`
- Review the test files in `/tests` for additional usage patterns
- See the conventions in `/CONVENTIONS.md`
