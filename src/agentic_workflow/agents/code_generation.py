"""Code Generation Agent for autonomous software development."""

import ast
import json
import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from agentic_workflow.agents.base import Agent, AgentResult, AgentTask
from agentic_workflow.core.config import get_config
from agentic_workflow.core.exceptions import AgentError, ValidationError
from agentic_workflow.utils.metrics import inc_model_fallback
from agentic_workflow.memory.interfaces import MemoryType


class CodeGenerationRequest(BaseModel):
    """Request for code generation."""

    prompt: str
    language: str = "python"
    style: str = "clean"  # clean, functional, object-oriented
    include_tests: bool = False
    include_docs: bool = True
    complexity: str = "medium"  # simple, medium, complex
    context: Optional[Dict[str, Any]] = None


class CodeGenerationResult(BaseModel):
    """Result of code generation."""

    code: str
    documentation: Optional[str] = None
    tests: Optional[str] = None
    explanation: str
    quality_score: float
    suggestions: List[str] = []
    dependencies: List[str] = []


class CodeTemplate:
    """Code templates and patterns for generation."""

    PYTHON_FUNCTION_TEMPLATE = """
def {function_name}({parameters}) -> {return_type}:
    \"\"\"{docstring}

    Args:
{args_docs}

    Returns:
        {return_doc}

    Raises:
{raises_docs}
    \"\"\"
    {implementation}
"""

    PYTHON_CLASS_TEMPLATE = """
class {class_name}:
    \"\"\"{class_docstring}

    Attributes:
{attributes_docs}
    \"\"\"

    def __init__(self, {init_parameters}):
        \"\"\"{init_docstring}

        Args:
{init_args_docs}
        \"\"\"
{init_implementation}

{methods}
"""

    PYTHON_TEST_TEMPLATE = """
import pytest
from unittest.mock import Mock, patch

from {module_name} import {class_or_function_name}


class Test{class_or_function_name}:
    \"\"\"Test cases for {class_or_function_name}.\"\"\"

    def test_{test_case_name}(self):
        \"\"\"Test {test_description}.\"\"\"
        # Arrange
        {test_setup}

        # Act
        {test_execution}

        # Assert
        {test_assertions}
"""


class CodeGenerationAgent(Agent):
    """Agent for generating high-quality code with comprehensive features.

    This agent specializes in autonomous code generation, providing:
    - OpenAI-powered code generation with multiple models
    - Code quality validation and improvement suggestions
    - Automatic documentation generation
    - Test case generation
    - Code pattern and template library
    - Multi-language support with Python as primary focus
    """

    def __init__(
        self,
        agent_id: str = "code_generation_agent",
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CodeGenerationAgent.

        Args:
            agent_id: Unique identifier for the agent
            config: Agent configuration including OpenAI settings
            **kwargs: Additional arguments passed to base Agent
        """
        super().__init__(agent_id, config, **kwargs)
        self.openai_client: Optional[AsyncOpenAI] = None
        self.templates = CodeTemplate()
        # Model selection: agent config -> global LLM config
        app_cfg = get_config()
        if app_cfg.llm.use_gpt5_preview:
            default_model = app_cfg.llm.gpt5_model_name
        else:
            default_model = app_cfg.llm.default_model or "gpt-4"
        self.model_name = self.config.get("model", default_model)
        self.temperature = self.config.get("temperature", 0.1)
        self.max_tokens = self.config.get("max_tokens", 2048)

        # Code quality thresholds
        self.min_quality_score = self.config.get("min_quality_score", 0.7)
        self.max_complexity = self.config.get("max_complexity", 10)

    async def initialize(self) -> None:
        """Initialize the Code Generation Agent."""
        await super().initialize()

        # Initialize OpenAI client
        config = get_config()
        api_key = config.llm.openai_api_key or self.config.get("openai_api_key")

        if not api_key:
            raise AgentError("OpenAI API key not configured")

        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.logger.info("OpenAI client initialized successfully")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute code generation task.

        Args:
            task: AgentTask containing code generation parameters

        Returns:
            AgentResult with generated code and metadata

        Raises:
            AgentError: If code generation fails
            ValidationError: If task parameters are invalid
        """
        start_time = datetime.now(UTC)
        self.logger.info(f"Executing code generation task: {task.task_id}")

        try:
            # Validate and parse request
            request = self._parse_generation_request(task)

            # Generate code using OpenAI
            generated_code = await self._generate_code_with_ai(request)

            # Validate and improve code quality
            quality_result = await self._validate_code_quality(
                generated_code, request.language
            )

            # Generate documentation if requested
            documentation = None
            if request.include_docs:
                documentation = await self._generate_documentation(
                    generated_code, request
                )

            # Generate tests if requested
            tests = None
            if request.include_tests:
                tests = await self._generate_tests(generated_code, request)

            # Create result
            result = CodeGenerationResult(
                code=quality_result["improved_code"],
                documentation=documentation,
                tests=tests,
                explanation=quality_result["explanation"],
                quality_score=quality_result["quality_score"],
                suggestions=quality_result["suggestions"],
                dependencies=quality_result["dependencies"],
            )

            # Store in memory for future reference
            if self.memory_manager:
                await self._store_generation_result(task, request, result)

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            return AgentResult(
                success=True,
                data=result.model_dump(),
                task_id=task.task_id,
                agent_id=self.agent_id,
                execution_time=execution_time,
                steps_taken=[
                    {"step": "parse_request", "status": "completed"},
                    {"step": "generate_code", "status": "completed"},
                    {
                        "step": "validate_quality",
                        "status": "completed",
                        "score": quality_result["quality_score"],
                    },
                    {
                        "step": "generate_documentation",
                        "status": "completed" if documentation else "skipped",
                    },
                    {
                        "step": "generate_tests",
                        "status": "completed" if tests else "skipped",
                    },
                    {
                        "step": "store_results",
                        "status": "completed" if self.memory_manager else "skipped",
                    },
                ],
            )

        except Exception as e:
            self.logger.error(f"Code generation failed for task {task.task_id}: {e}")
            # Raise AgentError instead of returning failed result
            raise AgentError(f"Code generation failed for task {task.task_id}: {e}")

    async def plan(
        self, objective: str, context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """Create execution plan for code generation objective.

        Args:
            objective: High-level code generation goal
            context: Additional context for planning

        Returns:
            List of AgentTask objects for the execution plan
        """
        self.logger.info(f"Planning code generation for objective: {objective}")

        context = context or {}
        tasks = []

        # Analyze the objective to determine task breakdown
        if "class" in objective.lower() or "object" in objective.lower():
            # Object-oriented development plan
            tasks.extend(
                [
                    AgentTask(
                        type="analyze_requirements",
                        prompt=f"Analyze requirements for: {objective}",
                        context=context,
                    ),
                    AgentTask(
                        type="design_class_structure",
                        prompt=f"Design class structure for: {objective}",
                        context=context,
                    ),
                    AgentTask(
                        type="generate_code",
                        prompt=f"Generate class implementation for: {objective}",
                        language="python",
                        style="object-oriented",
                        include_tests=True,
                        include_docs=True,
                        context=context,
                    ),
                    AgentTask(
                        type="validate_and_test",
                        prompt=f"Validate and test implementation for: {objective}",
                        context=context,
                    ),
                ]
            )
        elif "api" in objective.lower() or "endpoint" in objective.lower():
            # API development plan
            tasks.extend(
                [
                    AgentTask(
                        type="design_api_spec",
                        prompt=f"Design API specification for: {objective}",
                        context=context,
                    ),
                    AgentTask(
                        type="generate_api_code",
                        prompt=f"Generate API implementation for: {objective}",
                        language="python",
                        style="clean",
                        include_tests=True,
                        include_docs=True,
                        context=context,
                    ),
                    AgentTask(
                        type="generate_api_tests",
                        prompt=f"Generate comprehensive API tests for: {objective}",
                        context=context,
                    ),
                ]
            )
        else:
            # General function/module development
            tasks.extend(
                [
                    AgentTask(
                        type="generate_code",
                        prompt=objective,
                        language=context.get("language", "python"),
                        style=context.get("style", "clean"),
                        include_tests=context.get("include_tests", True),
                        include_docs=context.get("include_docs", True),
                        complexity=context.get("complexity", "medium"),
                        context=context,
                    ),
                ]
            )

        self.logger.info(f"Created execution plan with {len(tasks)} tasks")
        return tasks

    def get_capabilities(self) -> List[str]:
        """Get code generation agent capabilities."""
        return [
            "code_generation",
            "documentation_generation",
            "test_generation",
            "code_quality_validation",
            "multi_language_support",
            "template_based_generation",
            "pattern_recognition",
            "dependency_analysis",
        ]

    def _parse_generation_request(self, task: AgentTask) -> CodeGenerationRequest:
        """Parse agent task into code generation request.

        Args:
            task: AgentTask to parse

        Returns:
            CodeGenerationRequest object

        Raises:
            ValidationError: If task parameters are invalid
        """
        try:
            # Extract required parameters
            prompt = task.get("prompt")
            if not prompt:
                raise ValidationError("Code generation prompt is required")

            # Create request with defaults
            request = CodeGenerationRequest(
                prompt=prompt,
                language=task.get("language", "python"),
                style=task.get("style", "clean"),
                include_tests=task.get("include_tests", False),
                include_docs=task.get("include_docs", True),
                complexity=task.get("complexity", "medium"),
                context=task.get("context"),
            )

            self.logger.debug(f"Parsed generation request: {request}")
            return request

        except Exception as e:
            raise ValidationError(f"Invalid code generation request: {e}")

    async def _generate_code_with_ai(self, request: CodeGenerationRequest) -> str:
        """Generate code using OpenAI API.

        Args:
            request: Code generation request

        Returns:
            Generated code string

        Raises:
            AgentError: If code generation fails
        """
        if not self.openai_client:
            raise AgentError("OpenAI client not initialized")

        try:
            # Build comprehensive prompt
            system_prompt = self._build_system_prompt(request)
            user_prompt = self._build_user_prompt(request)

            self.logger.debug(f"Generating code with model: {self.model_name}")

            # Generate code with OpenAI
            # Try with configured model; if preview fails and health-check is enabled, fallback
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except (APIError, RateLimitError, AuthenticationError, Timeout) as e:
                cfg = get_config()
                default_model = cfg.llm.default_model or "gpt-4"
                if (
                    cfg.llm.enable_model_health_check
                    and cfg.llm.use_gpt5_preview
                    and self.model_name != default_model
                ):
                    self.logger.warning(
                        f"Model {self.model_name} failed, falling back to {default_model}: {e}"
                    )
                    inc_model_fallback(self.agent_id, self.model_name, default_model)
                    response = await self.openai_client.chat.completions.create(
                        model=default_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                else:
                    raise

            generated_code = response.choices[0].message.content
            if not generated_code:
                raise AgentError("Empty response from OpenAI")

            # Extract code from response (remove markdown formatting if present)
            generated_code = self._extract_code_from_response(generated_code)

            self.logger.info("Code generated successfully with OpenAI")
            return generated_code

        except Exception as e:
            raise AgentError(f"Failed to generate code with OpenAI: {e}")

    async def _validate_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """Validate and improve code quality.

        Args:
            code: Code to validate
            language: Programming language

        Returns:
            Dictionary with quality analysis results
        """
        quality_result: Dict[str, Any] = {
            "improved_code": code,
            "quality_score": 0.5,
            "explanation": "Code generated successfully",
            "suggestions": [],
            "dependencies": [],
        }

        try:
            if language.lower() == "python":
                # Parse Python code for syntax validation
                try:
                    ast.parse(code)
                    quality_result["quality_score"] += 0.3
                    quality_result["suggestions"].append("✅ Valid Python syntax")
                except SyntaxError as e:
                    quality_result["suggestions"].append(f"❌ Syntax error: {e}")
                    return quality_result

                # Check for docstrings
                if '"""' in code or "'''" in code:
                    quality_result["quality_score"] += 0.1
                    quality_result["suggestions"].append("✅ Includes docstrings")

                # Check for type hints
                if "->" in code or ": " in code:
                    quality_result["quality_score"] += 0.1
                    quality_result["suggestions"].append("✅ Includes type hints")

                # Extract dependencies
                import_lines = [
                    line.strip()
                    for line in code.split("\n")
                    if line.strip().startswith(("import ", "from "))
                ]
                quality_result["dependencies"] = import_lines

            quality_result["explanation"] = (
                f"Code quality analysis completed with score: {quality_result['quality_score']:.2f}"
            )

        except Exception as e:
            self.logger.warning(f"Quality validation failed: {e}")
            quality_result["suggestions"].append(f"⚠️ Quality validation error: {e}")

        return quality_result

    async def _generate_documentation(
        self, code: str, request: CodeGenerationRequest
    ) -> str:
        """Generate documentation for the code.

        Args:
            code: Generated code
            request: Original generation request

        Returns:
            Generated documentation
        """
        if not self.openai_client:
            return "Documentation generation failed: OpenAI client not initialized"

        try:
            doc_prompt = f"""
Generate comprehensive documentation for this {request.language} code:

```{request.language}
{code}
```

Include:
1. Overview of what the code does
2. Usage examples
3. Parameter descriptions
4. Return value descriptions
5. Any important notes or considerations

Format as markdown.
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation expert.",
                    },
                    {"role": "user", "content": doc_prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
            )

            return (
                response.choices[0].message.content or "Documentation generation failed"
            )

        except Exception as e:
            self.logger.warning(f"Documentation generation failed: {e}")
            return (
                f"# Documentation\n\nAutomatically generated documentation failed: {e}"
            )

    async def _generate_tests(self, code: str, request: CodeGenerationRequest) -> str:
        """Generate test cases for the code.

        Args:
            code: Generated code
            request: Original generation request

        Returns:
            Generated test code
        """
        if not self.openai_client:
            return "Test generation failed: OpenAI client not initialized"

        try:
            test_prompt = f"""
Generate comprehensive unit tests for this {request.language} code:

```{request.language}
{code}
```

Requirements:
1. Use pytest framework for Python
2. Include test cases for normal operation
3. Include edge cases and error conditions
4. Use appropriate mocking where needed
5. Follow testing best practices
6. Include docstrings for test methods

Generate complete, runnable test code.
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a testing expert who writes comprehensive unit tests.",
                    },
                    {"role": "user", "content": test_prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
            )

            return self._extract_code_from_response(
                response.choices[0].message.content or ""
            )

        except Exception as e:
            self.logger.warning(f"Test generation failed: {e}")
            return f"# Test generation failed: {e}"

    def _build_system_prompt(self, request: CodeGenerationRequest) -> str:
        """Build system prompt for code generation."""
        return f"""
You are an expert {request.language} developer specializing in {request.style} code.

Guidelines:
1. Write clean, readable, and maintainable code
2. Follow {request.language} best practices and conventions
3. Include proper error handling
4. Use descriptive variable and function names
5. Add type hints where applicable
6. Include docstrings for functions and classes
7. Keep complexity at {request.complexity} level
8. Ensure code is production-ready

Style preferences: {request.style}
Target complexity: {request.complexity}
Language: {request.language}
"""

    def _build_user_prompt(self, request: CodeGenerationRequest) -> str:
        """Build user prompt for code generation."""
        prompt = f"Generate {request.language} code for the following requirement:\n\n{request.prompt}"

        if request.context:
            prompt += f"\n\nAdditional context:\n{request.context}"

        prompt += "\n\nProvide only the code implementation without explanations."
        return prompt

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from OpenAI response, removing markdown formatting.

        Args:
            response: Raw response from OpenAI

        Returns:
            Clean code string
        """
        # Remove markdown code blocks
        code_block_pattern = r"```(?:\w+)?\n?(.*?)\n?```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)

        if matches:
            return str(matches[0].strip())

        # If no code blocks found, return the response as-is
        return str(response.strip())

    async def _store_generation_result(
        self,
        task: AgentTask,
        request: CodeGenerationRequest,
        result: CodeGenerationResult,
    ) -> None:
        """Store code generation result in memory.

        Args:
            task: Original task
            request: Generation request
            result: Generation result
        """
        if not self.memory_manager:
            self.logger.warning("Memory manager not available, skipping result storage")
            return

        try:
            # Serialize the content to JSON string as required by MemoryManager
            content_dict = {
                "task_id": task.task_id,
                "prompt": request.prompt,
                "language": request.language,
                "code": result.code,
                "quality_score": result.quality_score,
                "documentation": result.documentation,
                "tests": result.tests,
            }

            # Store using MemoryManager.store method signature
            entry_id = await self.memory_manager.store(
                content=json.dumps(content_dict),
                memory_type=MemoryType.LONG_TERM,
                metadata={
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "language": request.language,
                    "complexity": request.complexity,
                    "quality_score": result.quality_score,
                },
                entry_id=f"code_gen_{task.task_id}",
            )

            self.logger.debug(
                f"Stored generation result for task {task.task_id} with entry ID: {entry_id}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to store generation result: {e}")
