"""Tests for TestingAgent."""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.testing import TestingAgent
from agentic_workflow.core.exceptions import AgentError
from agentic_workflow.memory import MemoryManager


class TestTestingAgent:
    """Test cases for TestingAgent."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create agent instance for testing."""
        config = {
            "coverage_threshold": 0.8,
            "test_frameworks": ["pytest", "unittest"],
            "generate_edge_cases": True,
            "generate_error_cases": True,
            "max_tests_per_function": 5,
        }
        agent = TestingAgent(config=config)
        await agent.initialize()
        return agent

    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code for testing."""
        return """
def calculate_sum(a: int, b: int) -> int:
    \"\"\"Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        int: Sum of a and b
    \"\"\"
    return a + b

def divide_numbers(dividend: float, divisor: float) -> float:
    \"\"\"Divide two numbers.

    Args:
        dividend: Number to be divided
        divisor: Number to divide by

    Returns:
        float: Result of division

    Raises:
        ValueError: If divisor is zero
    \"\"\"
    if divisor == 0:
        raise ValueError("Cannot divide by zero")
    return dividend / divisor

class Calculator:
    \"\"\"Simple calculator class.\"\"\"

    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def get_history(self) -> list:
        \"\"\"Get calculation history.\"\"\"
        return self.history.copy()
"""

    @pytest.fixture
    def sample_test_code(self):
        """Sample test code for testing."""
        return """
import pytest
from calculator import Calculator, calculate_sum, divide_numbers


class TestCalculator:
    \"\"\"Test cases for Calculator class.\"\"\"

    @pytest.fixture
    def calc(self):
        \"\"\"Create calculator instance.\"\"\"
        return Calculator()

    def test_add(self, calc):
        \"\"\"Test addition functionality.\"\"\"
        result = calc.add(2, 3)
        assert result == 5
        assert len(calc.get_history()) == 1

    def test_get_history(self, calc):
        \"\"\"Test history functionality.\"\"\"
        calc.add(1, 1)
        calc.add(2, 2)
        history = calc.get_history()
        assert len(history) == 2


def test_calculate_sum():
    \"\"\"Test calculate_sum function.\"\"\"
    assert calculate_sum(2, 3) == 5
    assert calculate_sum(-1, 1) == 0
    assert calculate_sum(0, 0) == 0


def test_divide_numbers():
    \"\"\"Test divide_numbers function.\"\"\"
    assert divide_numbers(10, 2) == 5.0
    assert divide_numbers(7, 2) == 3.5

    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide_numbers(10, 0)
"""

    @pytest.fixture
    def invalid_code(self):
        """Invalid code for testing error handling."""
        return "This is not valid Python code at all!"

    @pytest.mark.asyncio
    async def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "testing_agent"
        assert agent.coverage_threshold == 0.8
        assert "pytest" in agent.test_frameworks
        assert agent.generate_edge_cases is True
        assert agent.max_tests_per_function == 5

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test agent capabilities."""
        capabilities = agent.get_capabilities()

        expected_capabilities = [
            "test_generation",
            "test_execution",
            "coverage_analysis",
            "test_strategy_planning",
            "test_validation",
            "unit_testing",
            "integration_testing",
            "functional_testing",
            "performance_testing",
            "test_result_analysis",
            "test_reporting",
        ]

        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_generate_tests_for_functions(self, agent, sample_python_code):
        """Test test generation for functions."""
        task = AgentTask(
            type="generate_tests",
            prompt="Generate unit tests for calculator functions",
            context={
                "code": sample_python_code,
                "language": "python",
                "test_type": "unit",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "generated_tests" in result.data
        assert result.data["test_count"] > 0
        assert result.data["test_type"] == "unit"
        assert result.data["language"] == "python"
        assert "code_analysis" in result.data
        assert "validation_results" in result.data
        assert "coverage_estimate" in result.data

        # Check code analysis
        code_analysis = result.data["code_analysis"]
        assert len(code_analysis["functions"]) >= 2  # calculate_sum, divide_numbers
        assert len(code_analysis["classes"]) >= 1  # Calculator
        assert code_analysis["testable_units"] > 0

    @pytest.mark.asyncio
    async def test_generate_tests_for_classes(self, agent, sample_python_code):
        """Test test generation for classes."""
        task = AgentTask(
            type="generate_tests",
            prompt="Generate integration tests for calculator",
            context={
                "code": sample_python_code,
                "language": "python",
                "test_type": "integration",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        generated_tests = result.data["generated_tests"]
        assert generated_tests["framework"] == "pytest"
        assert len(generated_tests["test_cases"]) > 0

        # Check for class test generation
        has_class_test = any(
            "Calculator" in test_case.get("target_class", "")
            for test_case in generated_tests["test_cases"]
        )
        assert has_class_test

    @pytest.mark.asyncio
    async def test_execute_tests(self, agent, sample_test_code):
        """Test test execution functionality."""
        task = AgentTask(
            type="execute_tests",
            prompt="Execute unit tests",
            context={"test_code": sample_test_code},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "execution_results" in result.data
        assert "result_analysis" in result.data
        assert "tests_run" in result.data
        assert "tests_passed" in result.data
        assert "tests_failed" in result.data
        assert "success_rate" in result.data

        # Check execution results structure
        execution_results = result.data["execution_results"]
        assert "success" in execution_results
        assert "execution_time" in execution_results
        assert "method" in execution_results

    @pytest.mark.asyncio
    async def test_analyze_coverage(self, agent, sample_python_code, sample_test_code):
        """Test coverage analysis."""
        task = AgentTask(
            type="analyze_coverage",
            prompt="Analyze test coverage",
            context={"source_code": sample_python_code, "test_code": sample_test_code},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "coverage_analysis" in result.data
        assert "coverage_percentage" in result.data
        assert "line_coverage" in result.data
        assert "branch_coverage" in result.data
        assert "function_coverage" in result.data
        assert "coverage_report" in result.data
        assert "meets_threshold" in result.data
        assert "uncovered_lines" in result.data

        # Check coverage metrics are percentages
        assert 0 <= result.data["coverage_percentage"] <= 1
        assert 0 <= result.data["line_coverage"] <= 1
        assert 0 <= result.data["branch_coverage"] <= 1
        assert 0 <= result.data["function_coverage"] <= 1

    @pytest.mark.asyncio
    async def test_create_test_strategy(self, agent):
        """Test test strategy creation."""
        task = AgentTask(
            type="test_strategy",
            prompt="Create comprehensive test strategy for web application",
            context={"project_type": "web_app", "complexity": "high"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "test_strategy" in result.data
        assert "project_analysis" in result.data
        assert "resource_estimates" in result.data
        assert "recommended_frameworks" in result.data
        assert "test_phases" in result.data
        assert "quality_gates" in result.data

        # Check strategy structure
        test_strategy = result.data["test_strategy"]
        assert "type" in test_strategy
        assert "frameworks" in test_strategy
        assert "phases" in test_strategy
        assert len(test_strategy["phases"]) > 0

        # Check resource estimates
        resource_estimates = result.data["resource_estimates"]
        assert "total_hours" in resource_estimates
        assert "estimated_cost" in resource_estimates
        assert "timeline_days" in resource_estimates

    @pytest.mark.asyncio
    async def test_validate_tests(self, agent, sample_test_code, sample_python_code):
        """Test test validation functionality."""
        task = AgentTask(
            type="validate_tests",
            prompt="Validate existing test suite",
            context={"test_code": sample_test_code, "source_code": sample_python_code},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "test_quality" in result.data
        assert "completeness_analysis" in result.data
        assert "recommendations" in result.data
        assert "quality_score" in result.data
        assert "completeness_score" in result.data
        assert "validation_passed" in result.data

        # Check test quality analysis
        test_quality = result.data["test_quality"]
        assert "overall_score" in test_quality
        assert "framework" in test_quality
        assert "test_count" in test_quality
        assert "has_fixtures" in test_quality
        assert "has_assertions" in test_quality

        # Check completeness analysis
        completeness_analysis = result.data["completeness_analysis"]
        assert "score" in completeness_analysis
        assert "covered_functions" in completeness_analysis
        assert "uncovered_functions" in completeness_analysis

    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, agent):
        """Test executing unknown task type raises error."""
        task = AgentTask(type="unknown_testing", prompt="Unknown testing type")

        with pytest.raises(AgentError, match="Testing execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_generate_tests_without_code(self, agent):
        """Test generating tests without code raises error."""
        task = AgentTask(type="generate_tests", prompt="")  # Empty prompt

        with pytest.raises(AgentError, match="Testing execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_execute_tests_without_test_code(self, agent):
        """Test executing tests without test code raises error."""
        task = AgentTask(type="execute_tests", prompt="Execute tests", context={})

        with pytest.raises(AgentError, match="Testing execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_analyze_coverage_without_source_code(self, agent):
        """Test coverage analysis without source code raises error."""
        task = AgentTask(
            type="analyze_coverage",
            prompt="Analyze coverage",
            context={"test_code": "test"},
        )

        with pytest.raises(AgentError, match="Testing execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_validate_tests_without_test_code(self, agent):
        """Test test validation without test code raises error."""
        task = AgentTask(type="validate_tests", prompt="Validate tests", context={})

        with pytest.raises(AgentError, match="Testing execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_plan_comprehensive_testing(self, agent):
        """Test planning for comprehensive testing."""
        objective = "Comprehensive test suite for user authentication system"

        tasks = await agent.plan(objective)

        assert len(tasks) >= 5  # Should have multiple testing tasks
        task_types = [task.get("type") for task in tasks]
        assert "test_strategy" in task_types
        assert "generate_tests" in task_types
        assert "execute_tests" in task_types
        assert "analyze_coverage" in task_types

        # Check for dependencies
        execution_task = next(
            (task for task in tasks if task.get("type") == "execute_tests"), None
        )
        assert execution_task is not None
        assert len(execution_task.get("dependencies", [])) > 0

    @pytest.mark.asyncio
    async def test_plan_unit_focused_testing(self, agent):
        """Test planning for unit-focused testing."""
        objective = "Unit tests for mathematical functions"

        tasks = await agent.plan(objective)

        assert len(tasks) >= 2
        task_types = [task.get("type") for task in tasks]
        assert "generate_tests" in task_types
        assert "execute_tests" in task_types

        # Check for unit test focus
        generation_task = next(
            (task for task in tasks if task.get("type") == "generate_tests"), None
        )
        assert generation_task is not None
        assert generation_task.get("context", {}).get("test_type") == "unit"

    @pytest.mark.asyncio
    async def test_plan_test_validation(self, agent):
        """Test planning for test validation."""
        objective = "Validate existing test suite quality"

        tasks = await agent.plan(objective)

        assert len(tasks) == 1
        assert tasks[0].get("type") == "validate_tests"
        assert tasks[0].get("priority") == "high"

    @pytest.mark.asyncio
    async def test_code_structure_analysis(self, agent, sample_python_code):
        """Test code structure analysis."""
        analysis = await agent._analyze_code_structure(sample_python_code, "python")

        assert "functions" in analysis
        assert "classes" in analysis
        assert "imports" in analysis
        assert "complexity" in analysis
        assert "testable_units" in analysis

        # Check functions analysis
        functions = analysis["functions"]
        assert len(functions) >= 2
        func_names = [func["name"] for func in functions]
        assert "calculate_sum" in func_names
        assert "divide_numbers" in func_names

        # Check classes analysis
        classes = analysis["classes"]
        assert len(classes) >= 1
        calc_class = next((cls for cls in classes if cls["name"] == "Calculator"), None)
        assert calc_class is not None
        assert "add" in calc_class["methods"]
        assert "get_history" in calc_class["methods"]

    @pytest.mark.asyncio
    async def test_function_test_generation(self, agent):
        """Test function test generation."""
        func_info = {
            "name": "calculate_sum",
            "args": ["a", "b"],
            "line_number": 1,
            "is_async": False,
            "docstring": "Calculate sum of two numbers",
        }

        test_case = await agent._generate_function_test(func_info, "unit")

        assert test_case["name"] == "test_calculate_sum"
        assert test_case["type"] == "unit"
        assert test_case["target_function"] == "calculate_sum"
        assert len(test_case["test_methods"]) >= 1

        # Check for basic test method
        basic_test = next(
            (
                method
                for method in test_case["test_methods"]
                if method["name"] == "test_calculate_sum_basic"
            ),
            None,
        )
        assert basic_test is not None
        assert "test_code" in basic_test

    @pytest.mark.asyncio
    async def test_class_test_generation(self, agent):
        """Test class test generation."""
        class_info = {
            "name": "Calculator",
            "methods": ["add", "subtract", "get_history"],
            "line_number": 10,
            "docstring": "Simple calculator class",
        }

        test_case = await agent._generate_class_test(class_info, "integration")

        assert test_case["name"] == "TestCalculator"
        assert test_case["type"] == "integration"
        assert test_case["target_class"] == "Calculator"
        assert len(test_case["test_methods"]) >= 3  # One for each public method
        assert len(test_case["fixtures"]) >= 1  # Setup fixture

        # Check for fixture
        fixture = test_case["fixtures"][0]
        assert fixture["name"] == "setup_calculator"
        assert "@pytest.fixture" in fixture["code"]

    @pytest.mark.asyncio
    async def test_test_data_generation(self, agent):
        """Test test data generation for function arguments."""
        # Test with different argument types
        args = ["user_id", "user_name", "count", "item_list", "config_dict", "value"]
        test_data = agent._generate_test_data(args)

        assert 'user_id = "test_id"' in test_data
        assert 'user_name = "test_name"' in test_data
        assert "count = 1" in test_data
        assert "item_list = []" in test_data
        assert "config_dict = {}" in test_data
        assert 'value = "test_value"' in test_data

        # Test with no arguments
        no_args_data = agent._generate_test_data([])
        assert "No arguments needed" in no_args_data

    @pytest.mark.asyncio
    async def test_test_validation(self, agent):
        """Test generated test validation."""
        valid_tests = {
            "test_cases": [
                {
                    "test_methods": [
                        {
                            "name": "test_valid",
                            "test_code": "def test_valid():\n    assert 1 == 1",
                        }
                    ]
                }
            ]
        }

        validation = await agent._validate_generated_tests(valid_tests, "python")
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

        # Test with invalid syntax
        invalid_tests = {
            "test_cases": [
                {
                    "test_methods": [
                        {
                            "name": "test_invalid",
                            "test_code": "def test_invalid(\n    assert 1 == 1",  # Missing closing paren
                        }
                    ]
                }
            ]
        }

        validation = await agent._validate_generated_tests(invalid_tests, "python")
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    @pytest.mark.asyncio
    async def test_coverage_estimation(self, agent):
        """Test coverage estimation."""
        code_analysis = {"testable_units": 4}
        generated_tests = {"test_cases": [{"name": "test1"}, {"name": "test2"}]}

        coverage = agent._estimate_coverage(code_analysis, generated_tests)

        assert 0 <= coverage <= 1
        assert isinstance(coverage, float)

    @pytest.mark.asyncio
    async def test_test_results_analysis(self, agent):
        """Test test results analysis."""
        execution_results = {
            "tests_run": 10,
            "tests_passed": 8,
            "tests_failed": 2,
        }

        analysis = await agent._analyze_test_results(execution_results)

        assert analysis["success_rate"] == 0.8
        assert "performance" in analysis
        assert "recommendations" in analysis

        # Test with poor results
        poor_results = {
            "tests_run": 10,
            "tests_passed": 3,
            "tests_failed": 7,
        }

        poor_analysis = await agent._analyze_test_results(poor_results)
        assert poor_analysis["success_rate"] == 0.3
        assert len(poor_analysis["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_test_quality_analysis(self, agent, sample_test_code):
        """Test test quality analysis."""
        quality = await agent._analyze_test_quality(sample_test_code)

        assert "overall_score" in quality
        assert "framework" in quality
        assert "test_count" in quality
        assert "has_fixtures" in quality
        assert "has_assertions" in quality
        assert "follows_naming_conventions" in quality

        # Should detect pytest framework
        assert quality["framework"] == "pytest"
        assert quality["has_fixtures"] is True
        assert quality["has_assertions"] is True

    @pytest.mark.asyncio
    async def test_test_completeness_analysis(
        self, agent, sample_test_code, sample_python_code
    ):
        """Test test completeness analysis."""
        completeness = await agent._analyze_test_completeness(
            sample_test_code, sample_python_code
        )

        assert "score" in completeness
        assert "covered_functions" in completeness
        assert "uncovered_functions" in completeness
        assert "test_to_code_ratio" in completeness
        assert "recommendations" in completeness

        # Should identify some coverage
        assert 0 <= completeness["score"] <= 1
        assert isinstance(completeness["covered_functions"], list)
        assert isinstance(completeness["uncovered_functions"], list)

    @pytest.mark.asyncio
    async def test_test_recommendations_generation(self, agent):
        """Test test recommendations generation."""
        test_quality = {
            "overall_score": 0.5,
            "has_fixtures": False,
            "has_documentation": False,
        }
        completeness_analysis = {
            "score": 0.6,
            "uncovered_functions": ["func1", "func2", "func3"],
        }

        recommendations = await agent._generate_test_recommendations(
            test_quality, completeness_analysis
        )

        assert len(recommendations) > 0
        assert any("quality" in rec.lower() for rec in recommendations)
        assert any("fixtures" in rec.lower() for rec in recommendations)
        assert any("coverage" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_strategy_determination(self, agent):
        """Test test strategy determination."""
        # Comprehensive strategy
        comprehensive_obj = "Complete testing for the entire application"
        assert agent._determine_test_strategy(comprehensive_obj, {}) == "comprehensive"

        # Unit focused strategy
        unit_obj = "Unit tests for mathematical functions"
        assert agent._determine_test_strategy(unit_obj, {}) == "unit_focused"

        # Validation strategy
        validation_obj = "Validate existing test suite"
        assert agent._determine_test_strategy(validation_obj, {}) == "validation"

    @pytest.mark.asyncio
    async def test_project_analysis_for_testing(self, agent):
        """Test project analysis for testing requirements."""
        objective = "Testing for REST API with database integration"
        context = {"project_type": "web_api"}

        analysis = await agent._analyze_project_for_testing(objective, context)

        assert "project_type" in analysis
        assert "complexity" in analysis
        assert "testing_requirements" in analysis
        assert "recommended_frameworks" in analysis
        assert "estimated_test_count" in analysis

        # Should detect API testing requirement
        assert "api" in analysis["testing_requirements"]

    @pytest.mark.asyncio
    async def test_test_strategy_development(self, agent):
        """Test test strategy development."""
        project_analysis = {
            "project_type": "web_app",
            "complexity": "high",
            "testing_requirements": ["unit", "integration", "api"],
            "recommended_frameworks": ["pytest"],
        }

        strategy = await agent._develop_test_strategy(project_analysis, {})

        assert "type" in strategy
        assert "frameworks" in strategy
        assert "phases" in strategy
        assert "quality_gates" in strategy

        assert len(strategy["phases"]) >= 3
        assert strategy["quality_gates"]["minimum_coverage"] == agent.coverage_threshold

    @pytest.mark.asyncio
    async def test_resource_estimation(self, agent):
        """Test testing resource estimation."""
        test_strategy = {
            "phases": [
                {"estimated_duration": 2.0},
                {"estimated_duration": 3.0},
                {"estimated_duration": 1.5},
            ]
        }

        estimates = await agent._estimate_testing_resources(test_strategy)

        assert "total_hours" in estimates
        assert "estimated_cost" in estimates
        assert "timeline_days" in estimates
        assert "resource_breakdown" in estimates

        assert estimates["total_hours"] == 6.5
        assert estimates["estimated_cost"] > 0
        assert estimates["timeline_days"] > 0

    @pytest.mark.asyncio
    async def test_memory_storage_integration(self, agent, sample_python_code):
        """Test memory storage integration."""
        # Mock memory manager
        memory_manager = AsyncMock(spec=MemoryManager)
        agent.memory_manager = memory_manager

        task = AgentTask(
            type="generate_tests",
            prompt="Generate tests",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        memory_manager.store.assert_called_once()

        # Check that the stored data includes test metrics
        call_args = memory_manager.store.call_args
        assert "test_count" in call_args.kwargs["metadata"]
        assert "coverage" in call_args.kwargs["metadata"]

    @pytest.mark.asyncio
    async def test_is_valid_code(self, agent, sample_python_code, invalid_code):
        """Test code validation."""
        # Valid Python code
        assert agent._is_valid_code(sample_python_code, "python") is True

        # Invalid code
        assert agent._is_valid_code(invalid_code, "python") is False

        # Empty code
        assert agent._is_valid_code("", "python") is False

        # Code snippet with keywords
        snippet = "def test(): return True"
        assert agent._is_valid_code(snippet, "python") is True

    @pytest.mark.asyncio
    async def test_template_initialization(self, agent):
        """Test test templates initialization."""
        templates = agent.test_templates

        assert "pytest" in templates
        assert "unittest" in templates
        assert "unit_test" in templates["pytest"]
        assert "integration_test" in templates["pytest"]

        # Check template contains placeholder variables
        pytest_template = templates["pytest"]["unit_test"]
        assert "{module_name}" in pytest_template
        assert "{function_name}" in pytest_template
        assert "{ClassName}" in pytest_template
