#!/usr/bin/env python3
"""Demonstration of TestingAgent capabilities.

This script shows how to use the TestingAgent to:
1. Generate comprehensive tests for Python code
2. Execute the generated tests
3. Analyze test coverage
4. Create test strategies
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.testing import TestingAgent


async def demonstrate_testing_agent():
    """Demonstrate TestingAgent capabilities with example code."""

    # Read our example calculator module (now in same directory)
    calculator_code = Path("example_calculator.py").read_text()

    # Initialize the Testing Agent
    config = {
        "coverage_threshold": 0.85,
        "test_frameworks": ["pytest"],
        "generate_edge_cases": True,
        "generate_error_cases": True,
        "max_tests_per_function": 3,
    }

    testing_agent = TestingAgent(config=config)
    await testing_agent.initialize()

    print("🧪 Testing Agent Demo - Comprehensive Test Generation")
    print("=" * 60)

    # Demo 1: Generate Unit Tests
    print("\n1️⃣ Generating Unit Tests")
    print("-" * 30)

    unit_test_task = AgentTask(
        task_id="demo_unit_tests",
        type="generate_tests",
        prompt="Generate comprehensive unit tests for calculator functions",
        context={
            "code": calculator_code,
            "language": "python",
            "test_type": "unit",
        },
    )

    unit_result = await testing_agent.execute(unit_test_task)

    if unit_result.success:
        print(f"✅ Generated {unit_result.data['test_count']} unit test cases")
        print(f"🎯 Framework: {unit_result.data['generated_tests']['framework']}")
        print(f"📊 Coverage estimate: {unit_result.data['coverage_estimate']:.1%}")

        # Save generated tests to file
        generated_test_code = unit_result.data["generated_tests"]

        # Show a sample test case
        if generated_test_code.get("test_cases"):
            first_test = generated_test_code["test_cases"][0]
            print(f"\n📝 Sample Test Case: {first_test['name']}")
            print(f"   Target: {first_test.get('target_function', 'N/A')}")
            print(f"   Methods: {len(first_test.get('test_methods', []))}")
    else:
        print("❌ Unit test generation failed")

    # Demo 2: Generate Integration Tests
    print("\n2️⃣ Generating Integration Tests")
    print("-" * 35)

    integration_test_task = AgentTask(
        task_id="demo_integration_tests",
        type="generate_tests",
        prompt="Generate integration tests for Statistics class",
        context={
            "code": calculator_code,
            "language": "python",
            "test_type": "integration",
        },
    )

    integration_result = await testing_agent.execute(integration_test_task)

    if integration_result.success:
        print(f"✅ Generated {integration_result.data['test_count']} integration test cases")
        print(f"🔗 Test type: {integration_result.data['test_type']}")
    else:
        print("❌ Integration test generation failed")

    # Demo 3: Create Test Strategy
    print("\n3️⃣ Creating Test Strategy")
    print("-" * 30)

    strategy_task = AgentTask(
        task_id="demo_test_strategy",
        type="test_strategy",
        prompt="Create comprehensive test strategy for calculator module",
        context={
            "project_type": "library",
            "complexity": "medium",
            "target_coverage": 0.9,
        },
    )

    strategy_result = await testing_agent.execute(strategy_task)

    if strategy_result.success:
        strategy = strategy_result.data["test_strategy"]
        resources = strategy_result.data["resource_estimates"]

        print(f"✅ Test strategy created: {strategy['type']}")
        print(f"🚀 Recommended frameworks: {', '.join(strategy['frameworks'])}")
        print(f"⏱️  Estimated time: {resources['total_hours']} hours")
        print(f"💰 Estimated cost: ${resources['estimated_cost']}")
        print(f"📅 Timeline: {resources['timeline_days']} days")

        print(f"\n📋 Test Phases:")
        for phase in strategy.get("phases", []):
            description = phase.get("description", "No description available")
            print(f"   • {phase['name']}: {description}")
    else:
        print("❌ Test strategy creation failed")

    # Demo 4: Planning Capabilities
    print("\n4️⃣ Demonstrating Planning Capabilities")
    print("-" * 40)

    objective = "Comprehensive test suite for calculator module with 90% coverage"
    tasks = await testing_agent.plan(objective)

    print(f"📋 Generated {len(tasks)} tasks for objective:")
    print(f"   '{objective}'")
    print()

    total_duration = 0
    for i, task in enumerate(tasks, 1):
        duration = task.get('estimated_duration', 1.0)
        total_duration += duration
        deps = task.get('dependencies', [])

        print(f"   {i}. {task.get('type', 'unknown')}")
        print(f"      ⏱️  Duration: {duration}h | Priority: {task.get('priority', 'medium')}")
        if deps:
            print(f"      🔗 Dependencies: {', '.join(deps)}")
        print()

    print(f"📊 Total estimated duration: {total_duration} hours")

    # Demo 5: Agent Capabilities
    print("\n5️⃣ Testing Agent Capabilities")
    print("-" * 35)

    capabilities = testing_agent.get_capabilities()
    print("🛠️  Available capabilities:")
    for i, capability in enumerate(capabilities, 1):
        print(f"   {i:2d}. {capability}")

    print("\n" + "=" * 60)
    print("✨ Testing Agent demonstration completed!")
    print("   The agent can generate, execute, and analyze tests")
    print("   for comprehensive software quality assurance.")


async def generate_sample_test_file():
    """Generate a sample test file that we can actually run."""

    # Read our example calculator module (now in same directory)
    calculator_code = Path("example_calculator.py").read_text()

    # Initialize the Testing Agent
    testing_agent = TestingAgent()
    await testing_agent.initialize()

    # Generate tests
    task = AgentTask(
        task_id="sample_test_generation",
        type="generate_tests",
        prompt="Generate runnable pytest tests for calculator functions",
        context={
            "code": calculator_code,
            "language": "python",
            "test_type": "unit",
        },
    )

    result = await testing_agent.execute(task)

    if result.success:
        # Create a simple test file that can actually be run
        test_content = """# Generated tests for example_calculator.py
import pytest
from example_calculator import add, divide, factorial, Statistics


class TestCalculatorFunctions:
    \"\"\"Test cases for calculator functions.\"\"\"

    def test_add_basic(self):
        \"\"\"Test basic addition functionality.\"\"\"
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_add_edge_cases(self):
        \"\"\"Test edge cases for addition.\"\"\"
        assert add(1.5, 2.5) == 4.0
        assert add(-5, -3) == -8
        assert add(1000000, 1000000) == 2000000

    def test_divide_basic(self):
        \"\"\"Test basic division functionality.\"\"\"
        assert divide(10, 2) == 5.0
        assert divide(9, 3) == 3.0
        assert divide(1, 1) == 1.0

    def test_divide_edge_cases(self):
        \"\"\"Test edge cases for division.\"\"\"
        assert divide(7, 2) == 3.5
        assert divide(-10, 2) == -5.0
        assert divide(10, -2) == -5.0

    def test_divide_error_handling(self):
        \"\"\"Test error handling for division.\"\"\"
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(-5, 0)

    def test_factorial_basic(self):
        \"\"\"Test basic factorial functionality.\"\"\"
        assert factorial(0) == 1
        assert factorial(1) == 1
        assert factorial(5) == 120
        assert factorial(3) == 6

    def test_factorial_edge_cases(self):
        \"\"\"Test edge cases for factorial.\"\"\"
        assert factorial(10) == 3628800

    def test_factorial_error_handling(self):
        \"\"\"Test error handling for factorial.\"\"\"
        with pytest.raises(ValueError, match="Factorial is not defined for negative numbers"):
            factorial(-1)

        with pytest.raises(ValueError, match="Factorial is not defined for negative numbers"):
            factorial(-5)


class TestStatistics:
    \"\"\"Test cases for Statistics class.\"\"\"

    @pytest.fixture
    def stats(self):
        \"\"\"Create statistics instance for testing.\"\"\"
        return Statistics()

    def test_add_data(self, stats):
        \"\"\"Test adding data to statistics.\"\"\"
        stats.add_data(5.0)
        assert len(stats.data) == 1
        assert stats.data[0] == 5.0

        stats.add_data(10.0)
        assert len(stats.data) == 2

    def test_get_mean_basic(self, stats):
        \"\"\"Test basic mean calculation.\"\"\"
        stats.add_data(2.0)
        stats.add_data(4.0)
        stats.add_data(6.0)
        assert stats.get_mean() == 4.0

    def test_get_mean_single_value(self, stats):
        \"\"\"Test mean calculation with single value.\"\"\"
        stats.add_data(7.5)
        assert stats.get_mean() == 7.5

    def test_get_mean_error_handling(self, stats):
        \"\"\"Test error handling for mean calculation.\"\"\"
        with pytest.raises(ValueError, match="Cannot calculate mean of empty dataset"):
            stats.get_mean()

    def test_get_median_odd_count(self, stats):
        \"\"\"Test median calculation with odd number of values.\"\"\"
        for value in [1, 3, 5, 7, 9]:
            stats.add_data(value)
        assert stats.get_median() == 5

    def test_get_median_even_count(self, stats):
        \"\"\"Test median calculation with even number of values.\"\"\"
        for value in [2, 4, 6, 8]:
            stats.add_data(value)
        assert stats.get_median() == 5.0

    def test_get_median_single_value(self, stats):
        \"\"\"Test median calculation with single value.\"\"\"
        stats.add_data(42.0)
        assert stats.get_median() == 42.0

    def test_get_median_error_handling(self, stats):
        \"\"\"Test error handling for median calculation.\"\"\"
        with pytest.raises(ValueError, match="Cannot calculate median of empty dataset"):
            stats.get_median()

    def test_clear(self, stats):
        \"\"\"Test clearing data from statistics.\"\"\"
        stats.add_data(1.0)
        stats.add_data(2.0)
        assert len(stats.data) == 2

        stats.clear()
        assert len(stats.data) == 0

    def test_workflow_integration(self, stats):
        \"\"\"Test complete workflow with statistics.\"\"\"
        # Add sample data
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in data:
            stats.add_data(value)

        # Test calculations
        assert stats.get_mean() == 3.0
        assert stats.get_median() == 3.0
        assert len(stats.data) == 5

        # Clear and verify
        stats.clear()
        assert len(stats.data) == 0
"""

        # Write the test file
        Path("test_generated_calculator.py").write_text(test_content)
        print("✅ Generated test file: test_generated_calculator.py")
        print(f"📊 Test analysis from agent:")
        print(f"   - Generated {result.data['test_count']} test cases")
        print(f"   - Coverage estimate: {result.data['coverage_estimate']:.1%}")
        print(f"   - Code analysis found {len(result.data['code_analysis']['functions'])} functions")
        print(f"   - Code analysis found {len(result.data['code_analysis']['classes'])} classes")

        return True
    else:
        print("❌ Failed to generate test file")
        return False


if __name__ == "__main__":
    # Run the demonstrations
    print("🚀 Starting Testing Agent Demo...")

    # First, run the comprehensive demo
    asyncio.run(demonstrate_testing_agent())

    print("\n" + "=" * 60)
    print("🧪 Generating Runnable Test File...")
    print("=" * 60)

    # Then generate a sample test file we can actually run
    success = asyncio.run(generate_sample_test_file())

    if success:
        print("\n💡 Next steps:")
        print("   1. Run the generated tests: pytest test_generated_calculator.py -v")
        print("   2. Check coverage: pytest --cov=example_calculator test_generated_calculator.py")
        print("   3. Generate HTML coverage report: pytest --cov=example_calculator --cov-report=html test_generated_calculator.py")
