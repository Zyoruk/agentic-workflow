"""Test cases for CodeGenerationAgent."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.code_generation import (
    CodeGenerationAgent,
    CodeGenerationRequest,
    CodeGenerationResult,
    CodeTemplate,
)
from agentic_workflow.core.exceptions import AgentError, ValidationError
from agentic_workflow.core.interfaces import ComponentStatus


class TestCodeGenerationAgent:
    """Test cases for CodeGenerationAgent."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create agent instance for testing."""
        config = {
            "model": "gpt-4",
            "temperature": 0.1,
            "max_tokens": 2048,
            "openai_api_key": "test-api-key",
        }
        agent = CodeGenerationAgent("test_code_gen_agent", config)

        # Mock the memory manager and guardrails
        agent.memory_manager = AsyncMock()
        agent.guardrails = AsyncMock()

        return agent

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
```python
def hello_world(name: str) -> str:
    \"\"\"Generate a greeting message.

    Args:
        name: Name of the person to greet

    Returns:
        Greeting message
    \"\"\"
    return f"Hello, {name}!"
```
"""
        return mock_response

    @pytest.fixture
    def simple_task(self):
        """Create a simple code generation task."""
        return AgentTask(
            type="generate_code",
            prompt="Create a hello world function that takes a name parameter",
            language="python",
            style="clean",
            include_tests=False,
            include_docs=True,
            complexity="simple",
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "test_code_gen_agent"
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.1
        assert agent.max_tokens == 2048
        assert agent.status == ComponentStatus.INITIALIZING

    @pytest.mark.asyncio
    async def test_agent_initialize_success(self, agent):
        """Test successful agent initialization."""
        with patch(
            "agentic_workflow.agents.code_generation.AsyncOpenAI"
        ) as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            await agent.initialize()

            assert agent.status == ComponentStatus.READY
            assert agent.openai_client == mock_client
            mock_openai.assert_called_once_with(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_agent_initialize_no_api_key(self):
        """Test agent initialization without API key."""
        agent = CodeGenerationAgent("test_agent", {})
        agent.memory_manager = AsyncMock()
        agent.guardrails = AsyncMock()

        with pytest.raises(AgentError, match="OpenAI API key not configured"):
            await agent.initialize()

    @pytest.mark.asyncio
    async def test_parse_generation_request_valid(self, agent, simple_task):
        """Test parsing valid generation request."""
        request = agent._parse_generation_request(simple_task)

        assert isinstance(request, CodeGenerationRequest)
        assert (
            request.prompt
            == "Create a hello world function that takes a name parameter"
        )
        assert request.language == "python"
        assert request.style == "clean"
        assert request.include_tests is False
        assert request.include_docs is True
        assert request.complexity == "simple"

    @pytest.mark.asyncio
    async def test_parse_generation_request_missing_prompt(self, agent):
        """Test parsing request with missing prompt."""
        task = AgentTask(type="generate_code", language="python")

        with pytest.raises(ValidationError, match="Code generation prompt is required"):
            agent._parse_generation_request(task)

    @pytest.mark.asyncio
    async def test_generate_code_with_ai(self, agent, mock_openai_response):
        """Test code generation with OpenAI API."""
        # Setup
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        request = CodeGenerationRequest(
            prompt="Create a hello world function",
            language="python",
            style="clean",
        )

        # Execute
        result = await agent._generate_code_with_ai(request)

        # Assert
        assert "def hello_world" in result
        assert "name: str" in result
        assert 'return f"Hello, {name}!"' in result
        agent.openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_code_with_ai_no_client(self, agent):
        """Test code generation without initialized client."""
        request = CodeGenerationRequest(prompt="test", language="python")

        with pytest.raises(AgentError, match="OpenAI client not initialized"):
            await agent._generate_code_with_ai(request)

    @pytest.mark.asyncio
    async def test_validate_code_quality_valid_python(self, agent):
        """Test code quality validation with valid Python code."""
        code = """
def hello_world(name: str) -> str:
    \"\"\"Generate a greeting message.\"\"\"
    return f"Hello, {name}!"
"""

        result = await agent._validate_code_quality(code, "python")

        assert result["quality_score"] > 0.5
        assert "✅ Valid Python syntax" in result["suggestions"]
        assert "✅ Includes docstrings" in result["suggestions"]
        assert "✅ Includes type hints" in result["suggestions"]

    @pytest.mark.asyncio
    async def test_validate_code_quality_invalid_python(self, agent):
        """Test code quality validation with invalid Python code."""
        code = "def hello_world(name: str -> str:"  # Invalid syntax

        result = await agent._validate_code_quality(code, "python")

        assert any(
            "❌ Syntax error" in suggestion for suggestion in result["suggestions"]
        )

    @pytest.mark.asyncio
    async def test_extract_code_from_response_with_markdown(self, agent):
        """Test code extraction from markdown-formatted response."""
        response = """
Here's the code:

```python
def hello():
    return "Hello, World!"
```

This function returns a greeting.
"""

        result = agent._extract_code_from_response(response)
        assert result == 'def hello():\n    return "Hello, World!"'

    @pytest.mark.asyncio
    async def test_extract_code_from_response_no_markdown(self, agent):
        """Test code extraction from response without markdown."""
        response = 'def hello():\n    return "Hello, World!"'

        result = agent._extract_code_from_response(response)
        assert result == response

    @pytest.mark.asyncio
    async def test_execute_simple_task(self, agent, simple_task, mock_openai_response):
        """Test executing a simple code generation task."""
        # Setup mocks
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        # Execute
        result = await agent.execute(simple_task)

        # Assert
        assert result.success is True
        assert result.task_id == simple_task.task_id
        assert result.agent_id == agent.agent_id
        assert "code" in result.data
        assert "quality_score" in result.data
        assert len(result.steps_taken) > 0

    @pytest.mark.asyncio
    async def test_execute_with_documentation_and_tests(
        self, agent, mock_openai_response
    ):
        """Test executing task with documentation and tests."""
        # Setup
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        task = AgentTask(
            type="generate_code",
            prompt="Create a calculator function",
            language="python",
            include_tests=True,
            include_docs=True,
        )

        # Execute
        result = await agent.execute(task)

        # Assert
        assert result.success is True
        assert result.data["documentation"] is not None
        assert result.data["tests"] is not None

        # Verify multiple OpenAI calls were made (code, docs, tests)
        assert agent.openai_client.chat.completions.create.call_count >= 3

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, agent, simple_task):
        """Test task execution with failure."""
        # Setup to cause failure
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Execute and expect AgentError to be raised
        with pytest.raises(AgentError, match="Code generation failed for task"):
            await agent.execute(simple_task)

    @pytest.mark.asyncio
    async def test_plan_class_objective(self, agent):
        """Test planning for class-based objective."""
        objective = "Create a User class with authentication methods"
        context = {"language": "python", "complexity": "medium"}

        tasks = await agent.plan(objective, context)

        assert len(tasks) == 4
        assert tasks[0]["type"] == "analyze_requirements"
        assert tasks[1]["type"] == "design_class_structure"
        assert tasks[2]["type"] == "generate_code"
        assert tasks[3]["type"] == "validate_and_test"

    @pytest.mark.asyncio
    async def test_plan_api_objective(self, agent):
        """Test planning for API-based objective."""
        objective = "Create a REST API endpoint for user management"

        tasks = await agent.plan(objective)

        assert len(tasks) == 3
        assert tasks[0]["type"] == "design_api_spec"
        assert tasks[1]["type"] == "generate_api_code"
        assert tasks[2]["type"] == "generate_api_tests"

    @pytest.mark.asyncio
    async def test_plan_general_objective(self, agent):
        """Test planning for general objective."""
        objective = "Create utility functions for data processing"

        tasks = await agent.plan(objective)

        assert len(tasks) == 1
        assert tasks[0]["type"] == "generate_code"
        assert tasks[0]["prompt"] == objective

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test getting agent capabilities."""
        capabilities = agent.get_capabilities()

        expected_capabilities = [
            "code_generation",
            "documentation_generation",
            "test_generation",
            "code_quality_validation",
            "multi_language_support",
            "template_based_generation",
            "pattern_recognition",
            "dependency_analysis",
        ]

        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, agent):
        """Test health check when agent is healthy."""
        agent.status = ComponentStatus.RUNNING

        response = await agent.health_check()

        assert response.success is True
        assert response.data["agent_id"] == agent.agent_id
        assert response.data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, agent):
        """Test health check when agent is unhealthy."""
        agent.status = ComponentStatus.ERROR

        response = await agent.health_check()

        assert response.success is False

    @pytest.mark.asyncio
    async def test_safe_execute_with_guardrails(
        self, agent, simple_task, mock_openai_response
    ):
        """Test safe execution with guardrails."""
        # Setup
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        agent.guardrails = AsyncMock()

        # Execute
        result = await agent.safe_execute(simple_task)

        # Assert
        assert result.success is True
        # Expect 2 calls: pre-execution and post-execution validation
        assert agent.guardrails.validate_input.call_count == 2

    @pytest.mark.asyncio
    async def test_safe_execute_with_error_handling(self, agent, simple_task):
        """Test safe execution with error handling."""
        # Setup to cause failure
        agent.openai_client = AsyncMock()
        agent.openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Test error")
        )
        agent.guardrails = AsyncMock()

        # Execute
        with pytest.raises(AgentError, match="failed to execute task"):
            await agent.safe_execute(simple_task)

        # Assert error handling was called
        agent.guardrails.handle_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_generation_result(self, agent, simple_task):
        """Test storing generation result in memory."""
        # Setup
        request = CodeGenerationRequest(prompt="test", language="python")
        result = CodeGenerationResult(
            code="test code",
            explanation="test explanation",
            quality_score=0.8,
        )
        agent.memory_manager = AsyncMock()
        agent.memory_manager.store = AsyncMock(return_value="test_entry_id")

        # Execute
        await agent._store_generation_result(simple_task, request, result)

        # Assert
        agent.memory_manager.store.assert_called_once()

        # Check the call arguments (using keyword arguments)
        call_kwargs = agent.memory_manager.store.call_args.kwargs
        assert "content" in call_kwargs
        assert "memory_type" in call_kwargs
        assert "metadata" in call_kwargs
        assert "entry_id" in call_kwargs

        # Parse the JSON content to verify it contains expected data
        content_dict = json.loads(call_kwargs["content"])
        assert content_dict["code"] == "test code"
        assert content_dict["quality_score"] == 0.8

    def test_code_template_class(self):
        """Test CodeTemplate class has required templates."""
        template = CodeTemplate()

        assert hasattr(template, "PYTHON_FUNCTION_TEMPLATE")
        assert hasattr(template, "PYTHON_CLASS_TEMPLATE")
        assert hasattr(template, "PYTHON_TEST_TEMPLATE")

        assert "{function_name}" in template.PYTHON_FUNCTION_TEMPLATE
        assert "{class_name}" in template.PYTHON_CLASS_TEMPLATE
        assert "pytest" in template.PYTHON_TEST_TEMPLATE

    @pytest.mark.asyncio
    async def test_build_system_prompt(self, agent):
        """Test building system prompt."""
        request = CodeGenerationRequest(
            prompt="test", language="python", style="clean", complexity="medium"
        )

        prompt = agent._build_system_prompt(request)

        assert "python developer" in prompt.lower()
        assert "clean code" in prompt.lower()
        assert "medium level" in prompt.lower()

    @pytest.mark.asyncio
    async def test_build_user_prompt(self, agent):
        """Test building user prompt."""
        request = CodeGenerationRequest(
            prompt="Create a function",
            language="python",
            context={"additional": "info"},
        )

        prompt = agent._build_user_prompt(request)

        assert "Create a function" in prompt
        assert "python code" in prompt.lower()
        assert "additional" in prompt


class TestCodeGenerationAgentIntegration:
    """Integration tests for CodeGenerationAgent."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_full_workflow(self):
        """Test complete agent workflow from creation to execution."""
        # This would require actual OpenAI API key for full integration
        # For now, we'll mock the OpenAI calls but test the full flow

        config = {
            "model": "gpt-4",
            "temperature": 0.1,
            "openai_api_key": "test-key",
        }

        agent = CodeGenerationAgent("integration_test_agent", config)
        agent.memory_manager = AsyncMock()
        agent.guardrails = AsyncMock()

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
```python
def fibonacci(n: int) -> int:
    \"\"\"Calculate nth Fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```
"""

        with patch(
            "agentic_workflow.agents.code_generation.AsyncOpenAI"
        ) as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            # Initialize agent
            await agent.initialize()
            await agent.start()

            # Create and execute task
            task = AgentTask(
                type="generate_code",
                prompt="Create a fibonacci function",
                language="python",
                include_tests=True,
                include_docs=True,
            )

            result = await agent.safe_execute(task)

            # Verify results
            assert result.success is True
            assert "fibonacci" in result.data["code"]
            assert result.data["quality_score"] > 0.5

            # Verify agent state
            assert agent.status == ComponentStatus.RUNNING
            history = agent.get_execution_history()
            assert len(history) == 1
            assert history[0]["success"] is True

            # Cleanup
            await agent.stop()
            assert agent.status == ComponentStatus.STOPPED
