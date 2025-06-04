# Agentic Workflow Examples

This directory contains practical examples demonstrating various components and capabilities of the Agentic Workflow System.

## Testing Agent Examples

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
| **Memory** | Multi-store memory operations | `memory_*.py` | Redis, Weaviate |
| **Safety** | Validation and error handling | `guardrails_example.py` | None |
| **Workflow** | Agent orchestration | `basic_workflow_example.py` | Redis |

## Learning Path

1. **Start with Testing Agent** - Shows core agent capabilities without external dependencies
2. **Explore Memory System** - Learn about data persistence and retrieval
3. **Understand Guardrails** - See how safety and validation work
4. **Try Workflow Orchestration** - Coordinate multiple agents

## Contributing Examples

When adding new examples:

1. **Follow naming convention**: `{component}_example.py` or `{feature}_demo.py`
2. **Include comprehensive docstrings** explaining what the example demonstrates
3. **Add error handling** for graceful failure when services are unavailable
4. **Update this README** with example descriptions
5. **Include sample output** in comments or separate files

## Support

For questions about examples or to report issues:
- Check the main project documentation in `/docs`
- Review the test files in `/tests` for additional usage patterns
- See the conventions in `/CONVENTIONS.md`
