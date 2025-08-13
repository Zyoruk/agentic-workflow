# User Guide: Reasoning Patterns and Tool Integration

This guide provides practical examples and workflows for using the advanced reasoning patterns and tool integration system in real-world scenarios.

## 🚀 Quick Start

### Installation and Setup

```bash
# 1. Install the package
make install

# 2. Verify installation  
python -c "from agentic_workflow.core.reasoning import ReasoningEngine; print('Reasoning OK')"
python -c "from agentic_workflow.tools import ToolManager; print('Tools OK')"

# 3. Run demonstrations
python examples/reasoning_patterns_demo.py
python examples/tool_system_demo.py
```

## 🧠 Reasoning Patterns in Practice

### When to Use Each Pattern

#### Chain of Thought (CoT) - Best For:
- **Strategic planning and analysis**
- **Complex problem decomposition** 
- **Architectural design decisions**
- **Theoretical problem solving**
- **One-time analysis tasks**

#### ReAct (Reasoning + Acting) - Best For:
- **Implementation tasks**
- **Debugging and troubleshooting**
- **Iterative development processes**
- **Tasks requiring external feedback**
- **Dynamic problem-solving scenarios**

### Real-World Examples

#### Strategic Planning with CoT
```python
from agentic_workflow.core.reasoning import ReasoningEngine

async def strategic_planning_example():
    reasoning_engine = ReasoningEngine()
    
    # Complex strategic analysis
    result = reasoning_engine.reason(
        task_id="strategic_planning",
        agent_id="strategic_planner",
        objective="Design a scalable microservices architecture for a social media platform handling 1M+ users",
        pattern="chain_of_thought"
    )
    
    print(f"Strategic Analysis Complete")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Reasoning Steps: {len(result.steps)}")
    
    # View the reasoning process
    for i, step in enumerate(result.steps, 1):
        print(f"\nStep {i}: {step.question}")
        print(f"Analysis: {step.thought}")
        print(f"Confidence: {step.confidence:.1%}")
    
    print(f"\nFinal Recommendation: {result.final_answer}")
    
    return result

# Run strategic planning
strategic_result = asyncio.run(strategic_planning_example())
```

#### Implementation with ReAct
```python
async def implementation_example():
    reasoning_engine = ReasoningEngine()
    
    # Iterative implementation task
    result = reasoning_engine.reason(
        task_id="feature_implementation",
        agent_id="developer_agent", 
        objective="Implement a real-time notification system with WebSocket support",
        pattern="react"
    )
    
    print(f"Implementation Analysis Complete")
    print(f"Final Confidence: {result.confidence:.1%}")
    
    # View reasoning-action-observation cycles
    for step in result.steps:
        if step.action:
            print(f"\n🤔 Reasoning: {step.thought}")
            print(f"⚡ Action: {step.action}")
            print(f"👁️ Observation: {step.observation}")
    
    return result

# Run implementation planning
impl_result = asyncio.run(implementation_example())
```

## 🔧 Tool Integration Workflows

### Basic Tool Usage

```python
from agentic_workflow.tools import ToolManager
import asyncio

async def basic_tool_workflow():
    # Initialize tool manager
    manager = ToolManager()
    await manager.initialize()
    
    # 1. File Operations
    file_result = await manager.execute_tool("filesystem_tool", {
        "operation": "write",
        "path": "data/sample.txt",
        "content": "Sample data for analysis: 10, 20, 30, 40, 50"
    }, agent_id="workflow_agent")
    
    # 2. Text Processing
    text_result = await manager.execute_tool("text_processing_tool", {
        "operation": "analyze", 
        "text": file_result.result["content"]
    }, agent_id="workflow_agent")
    
    # 3. Data Analysis
    numbers = [10, 20, 30, 40, 50]
    analysis_result = await manager.execute_tool("data_analysis_tool", {
        "operation": "statistics",
        "data": numbers
    }, agent_id="workflow_agent")
    
    print(f"Text Analysis: {text_result.result}")
    print(f"Statistical Analysis: {analysis_result.result}")
    
    return analysis_result

# Run basic workflow
basic_result = asyncio.run(basic_tool_workflow())
```

### Advanced Tool Discovery and Recommendations

```python
async def tool_discovery_example():
    manager = ToolManager()
    await manager.initialize()
    
    # Discover available tools
    all_tools = manager.registry.list_tools()
    print(f"Available tools: {len(all_tools)}")
    
    for tool_id, info in all_tools.items():
        print(f"- {tool_id}: {info.description}")
    
    # Search for specific capabilities
    text_tools = manager.registry.search_tools("text processing")
    analysis_tools = manager.registry.search_tools("", category="analysis")
    
    print(f"\nText processing tools: {[t.tool_id for t in text_tools]}")
    print(f"Analysis tools: {[t.tool_id for t in analysis_tools]}")
    
    # Get recommendations for tasks
    recommendations = manager.recommend_tools(
        "analyze customer feedback data and generate insights",
        category="analysis"
    )
    
    print(f"\nRecommended tools:")
    for rec in recommendations:
        print(f"- {rec.tool_id}: {rec.confidence:.1%} confidence")
        print(f"  Reason: {rec.reason}")
    
    return recommendations

# Run tool discovery
recommendations = asyncio.run(tool_discovery_example())
```

## 🤖 Integrated Agent Workflows

### Enhanced Planning Agent

```python
from agentic_workflow.agents.planning import PlanningAgent
from agentic_workflow.tools import ToolManager

async def enhanced_agent_workflow():
    # Initialize components
    planner = PlanningAgent(agent_id="enhanced_planner")
    tools = ToolManager()
    await tools.initialize()
    
    # Strategic analysis with reasoning
    objective = "Develop a comprehensive testing strategy for microservices"
    
    analysis = planner.analyze_objective(
        objective,
        use_reasoning=True  # Enable Chain of Thought reasoning
    )
    
    print(f"Objective: {objective}")
    print(f"Analysis: {analysis['analysis']}")
    print(f"Reasoning Confidence: {analysis['confidence']:.1%}")
    
    # Access detailed reasoning path
    if 'reasoning_path' in analysis:
        reasoning = analysis['reasoning_path']
        print(f"\nReasoning Steps: {len(reasoning.steps)}")
        
        for step in reasoning.steps:
            print(f"- {step.question}: {step.thought}")
    
    # Execute analysis tools
    test_data = [85, 92, 78, 95, 88, 90, 82]  # Test coverage percentages
    stats_result = await tools.execute_tool("data_analysis_tool", {
        "operation": "statistics",
        "data": test_data
    }, agent_id=planner.agent_id)
    
    print(f"\nTest Coverage Analysis: {stats_result.result}")
    
    return analysis, stats_result

# Run enhanced agent workflow
analysis, stats = asyncio.run(enhanced_agent_workflow())
```

### Multi-Step Data Processing Pipeline

```python
async def data_processing_pipeline():
    """Complete data processing workflow using reasoning and tools."""
    
    # Initialize systems
    reasoning_engine = ReasoningEngine()
    tool_manager = ToolManager()
    await tool_manager.initialize()
    
    # Step 1: Plan the data processing approach
    plan = reasoning_engine.reason(
        task_id="data_processing_plan",
        agent_id="data_processor",
        objective="Process sales data file, analyze trends, and generate insights report",
        pattern="chain_of_thought"
    )
    
    print(f"Data Processing Plan (Confidence: {plan.confidence:.1%}):")
    for step in plan.steps:
        print(f"- {step.question}: {step.thought}")
    
    # Step 2: Create sample data
    sample_data = [
        "Sales Data Report",
        "Q1: $125,000", "Q2: $150,000", "Q3: $175,000", "Q4: $200,000",
        "Growth trend: 20% quarterly increase",
        "Top products: Product A (40%), Product B (30%), Product C (30%)"
    ]
    
    # Step 3: File operations
    write_result = await tool_manager.execute_tool("filesystem_tool", {
        "operation": "write",
        "path": "data/sales_report.txt",
        "content": "\n".join(sample_data)
    }, agent_id="data_processor")
    
    # Step 4: Text analysis
    text_analysis = await tool_manager.execute_tool("text_processing_tool", {
        "operation": "analyze",
        "text": "\n".join(sample_data)
    }, agent_id="data_processor")
    
    # Step 5: Numerical data analysis
    sales_numbers = [125000, 150000, 175000, 200000]
    numerical_analysis = await tool_manager.execute_tool("data_analysis_tool", {
        "operation": "statistics", 
        "data": sales_numbers
    }, agent_id="data_processor")
    
    # Step 6: Generate insights using ReAct
    insights = reasoning_engine.reason(
        task_id="sales_insights",
        agent_id="data_processor",
        objective=f"Generate business insights from sales data analysis: {numerical_analysis.result}",
        pattern="react"
    )
    
    # Step 7: Create final report
    report_content = f"""
Sales Data Analysis Report
=========================

Text Analysis: {text_analysis.result}

Statistical Analysis: {numerical_analysis.result}

Business Insights (Confidence: {insights.confidence:.1%}):
{insights.final_answer}

Reasoning Process:
"""
    
    for step in insights.steps:
        if step.action:
            report_content += f"\n- Action: {step.action}"
            report_content += f"\n  Result: {step.observation}"
    
    # Step 8: Save final report
    report_result = await tool_manager.execute_tool("filesystem_tool", {
        "operation": "write",
        "path": "reports/sales_analysis_final.txt",
        "content": report_content
    }, agent_id="data_processor")
    
    print(f"\n✅ Data processing pipeline complete!")
    print(f"📊 Plan confidence: {plan.confidence:.1%}")
    print(f"🧠 Insights confidence: {insights.confidence:.1%}")
    print(f"📁 Report saved: {report_result.success}")
    
    return plan, insights, report_result

# Run complete data processing pipeline
plan, insights, report = asyncio.run(data_processing_pipeline())
```

## 🔄 Performance Optimization

### Monitoring and Analytics

```python
async def performance_monitoring_example():
    manager = ToolManager()
    await manager.initialize()
    
    # Execute some operations for metrics
    for i in range(5):
        await manager.execute_tool("data_analysis_tool", {
            "operation": "statistics",
            "data": [i*10, i*20, i*30]
        }, agent_id=f"test_agent_{i}")
    
    # Get tool performance metrics
    tool_metrics = manager.get_tool_metrics("data_analysis_tool")
    print(f"Data Analysis Tool Metrics:")
    print(f"- Total executions: {tool_metrics.total_executions}")
    print(f"- Success rate: {tool_metrics.success_rate:.1%}")
    print(f"- Average execution time: {tool_metrics.avg_execution_time}ms")
    
    # Get system-wide metrics
    system_metrics = manager.get_system_metrics()
    print(f"\nSystem Metrics:")
    print(f"- Total tools: {system_metrics.total_tools}")
    print(f"- Total executions: {system_metrics.total_executions}")
    
    # Get system status
    status = manager.get_system_status()
    print(f"\nSystem Status:")
    print(f"- Health: {status.health}")
    print(f"- Active executions: {status.active_executions}")
    print(f"- Memory usage: {status.memory_usage}")
    
    return tool_metrics, system_metrics, status

# Run performance monitoring
tool_perf, sys_perf, status = asyncio.run(performance_monitoring_example())
```

### Concurrent Tool Execution

```python
async def concurrent_execution_example():
    manager = ToolManager()
    await manager.initialize()
    
    # Prepare multiple tasks
    tasks = [
        manager.execute_tool("data_analysis_tool", {
            "operation": "statistics", 
            "data": [i*10 + j for j in range(5)]
        }, agent_id=f"concurrent_agent_{i}")
        for i in range(3)
    ]
    
    # Execute concurrently
    results = await asyncio.gather(*tasks)
    
    print(f"Concurrent execution completed:")
    for i, result in enumerate(results):
        print(f"Task {i+1}: Success={result.success}, Time={result.execution_time_ms}ms")
    
    return results

# Run concurrent execution
concurrent_results = asyncio.run(concurrent_execution_example())
```

## ⚠️ Error Handling and Recovery

### Robust Error Handling

```python
from agentic_workflow.core.exceptions import ReasoningError
from agentic_workflow.tools.exceptions import ToolExecutionError

async def error_handling_example():
    reasoning_engine = ReasoningEngine()
    tool_manager = ToolManager()
    await tool_manager.initialize()
    
    # Test reasoning error handling
    try:
        result = reasoning_engine.reason(
            task_id="test_task",
            agent_id="test_agent",
            objective="", # Empty objective to trigger error
            pattern="chain_of_thought"
        )
    except ReasoningError as e:
        print(f"Reasoning Error: {e.message}")
        print(f"Error Type: {e.error_type}")
    
    # Test tool error handling
    try:
        result = await tool_manager.execute_tool("nonexistent_tool", {})
    except ToolExecutionError as e:
        print(f"Tool Error: {e.message}")
    
    # Test parameter validation
    try:
        result = await tool_manager.execute_tool("filesystem_tool", {
            "operation": "invalid_operation"
        }, agent_id="test_agent")
    except ToolExecutionError as e:
        print(f"Validation Error: {e.message}")
    
    print("Error handling demonstration complete")

# Run error handling examples
asyncio.run(error_handling_example())
```

## 🏆 Best Practices

### 1. Reasoning Pattern Selection
```python
def choose_reasoning_pattern(task_type: str) -> str:
    """Choose appropriate reasoning pattern based on task type."""
    
    strategic_tasks = ["planning", "architecture", "analysis", "design"]
    implementation_tasks = ["coding", "debugging", "testing", "deployment"]
    
    if any(keyword in task_type.lower() for keyword in strategic_tasks):
        return "chain_of_thought"
    elif any(keyword in task_type.lower() for keyword in implementation_tasks):
        return "react"
    else:
        return "chain_of_thought"  # Default to systematic analysis
```

### 2. Tool Selection Strategy
```python
async def smart_tool_selection(task_description: str, manager: ToolManager):
    """Intelligently select tools for a task."""
    
    # Get recommendations
    recommendations = manager.recommend_tools(task_description, limit=3)
    
    # Choose highest confidence tool above threshold
    for rec in recommendations:
        if rec.confidence > 0.7:  # 70% confidence threshold
            return rec.tool_id
    
    # Fallback to manual selection
    if "file" in task_description.lower():
        return "filesystem_tool"
    elif "text" in task_description.lower():
        return "text_processing_tool"
    elif "data" in task_description.lower():
        return "data_analysis_tool"
    
    return None
```

### 3. Performance Optimization
```python
async def optimized_workflow():
    """Example of performance-optimized workflow."""
    
    # Use connection pooling
    tool_manager = ToolManager()
    await tool_manager.initialize()
    
    # Configure for performance
    tool_manager.configure({
        "max_concurrent_executions": 10,
        "cache_enabled": True,
        "cache_ttl": 300
    })
    
    # Batch operations when possible
    tasks = []
    for i in range(5):
        task = tool_manager.execute_tool("data_analysis_tool", {
            "operation": "statistics",
            "data": [i, i+1, i+2]
        }, agent_id=f"batch_agent_{i}")
        tasks.append(task)
    
    # Execute concurrently
    results = await asyncio.gather(*tasks)
    
    return results
```

## 📚 Complete Examples

For comprehensive demonstrations, see:

1. **`examples/reasoning_patterns_demo.py`** - Interactive reasoning pattern exploration
2. **`examples/tool_system_demo.py`** - Complete tool system showcase
3. **`tests/unit/core/test_reasoning.py`** - Detailed reasoning test examples
4. **`tests/unit/tools/test_tools.py`** - Comprehensive tool integration tests

## 🔄 Next Steps

With these capabilities mastered, you can:

1. **Build Custom Tools**: Extend the tool portfolio for specific domains
2. **Create Complex Workflows**: Chain reasoning and tool execution for sophisticated automation
3. **Integrate with Agents**: Enhance existing agents with reasoning and tool capabilities
4. **Scale Operations**: Use concurrent execution and performance monitoring for production deployment

The reasoning patterns and tool integration system provide the foundation for building sophisticated AI agents capable of autonomous decision-making and task execution.