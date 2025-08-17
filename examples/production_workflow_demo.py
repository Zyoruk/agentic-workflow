#!/usr/bin/env python3
"""
Production Workflow Demonstration

This example demonstrates the full capabilities of the Agentic Workflow System
in a comprehensive, production-ready scenario showcasing:
- Multi-agent coordination
- Advanced reasoning patterns (CoT, ReAct, RAISE)
- Tool integration and discovery
- Memory management and persistence
- Error handling and guardrails

Usage:
    python examples/production_workflow_demo.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from agentic_workflow import __version__
from agentic_workflow.agents import create_agent, get_available_agent_types
from agentic_workflow.agents.base import AgentTask
from agentic_workflow.core.reasoning import ReasoningEngine
from agentic_workflow.core.communication import CommunicationManager, setup_agent_communication
from agentic_workflow.core.config import get_config
from agentic_workflow.memory.manager import MemoryManager
from agentic_workflow.tools import ToolManager


async def demonstrate_production_workflow():
    """Demonstrate a complete production workflow."""
    print(f"🚀 Agentic Workflow System v{__version__} - Production Demo")
    print("=" * 80)
    print()
    
    # Initialize core components
    print("🔧 Initializing Core Components...")
    config = get_config()
    memory_manager = MemoryManager()
    comm_manager = CommunicationManager()
    tool_manager = ToolManager()
    
    await memory_manager.initialize()
    await tool_manager.initialize()
    
    print(f"✅ Memory manager initialized")
    print(f"✅ Communication manager ready")
    print(f"✅ Tool manager with {len(tool_manager.registry.list_tools())} tools")
    print()
    
    # Create agents for the workflow
    print("🤖 Creating Agent Team...")
    agents = {
        'requirements': create_agent('requirement_engineering', agent_id='req_engineer'),
        'planner': create_agent('planning', agent_id='project_planner'), 
        'developer': create_agent('code_generation', agent_id='senior_dev'),
        'tester': create_agent('testing', agent_id='qa_engineer'),
        'reviewer': create_agent('review', agent_id='tech_lead'),
        'cicd': create_agent('cicd', agent_id='devops_engineer'),
        'manager': create_agent('program_manager', agent_id='project_manager')
    }
    
    # Initialize agents
    for name, agent in agents.items():
        await agent.initialize()
        print(f"✅ {agent.__class__.__name__} ({name}) initialized")
    
    print()
    
    # Setup communication network
    print("📡 Setting Up Multi-Agent Communication...")
    for name, agent in agents.items():
        await setup_agent_communication(agent.agent_id, comm_manager)
    print("✅ Agent communication network established")
    print()
    
    # Demonstrate workflow: E-commerce Platform Development
    print("💼 PRODUCTION WORKFLOW: E-commerce Platform Development")
    print("=" * 60)
    
    # Phase 1: Requirements Engineering
    print("\n🎯 Phase 1: Requirements Analysis")
    req_task = AgentTask(
        type="analyze_requirements",
        project_description="Modern e-commerce platform with microservices architecture",
        stakeholders=["Product Owner", "Tech Lead", "Business Analyst"],
        business_goals=[
            "Handle 100k concurrent users",
            "Support multiple payment gateways", 
            "Mobile-first responsive design",
            "Real-time inventory management",
            "99.9% uptime SLA"
        ],
        constraints={
            "budget": "$200k development budget",
            "timeline": "6 months to MVP",
            "compliance": "PCI DSS, GDPR compliant",
            "technology": "Cloud-native, containerized"
        }
    )
    
    req_result = await agents['requirements'].execute(req_task)
    print(f"✅ Requirements analyzed: {req_result.success}")
    if req_result.success:
        requirements = req_result.data.get('requirements', [])
        print(f"📋 Identified {len(requirements)} key requirements")
    print()
    
    # Phase 2: Strategic Planning with Reasoning
    print("📊 Phase 2: Strategic Planning with Advanced Reasoning")
    reasoning_engine = ReasoningEngine(
        agent_id="project_planner",
        memory_manager=memory_manager,
        communication_manager=comm_manager
    )
    
    # Use RAISE reasoning pattern for collaborative planning
    planning_objective = """
    Create a comprehensive project plan for the e-commerce platform based on the analyzed requirements.
    Consider architecture decisions, technology stack, development phases, and risk mitigation.
    """
    
    reasoning_result = await reasoning_engine.reason(
        task_id="ecommerce_planning",
        agent_id="project_planner", 
        objective=planning_objective,
        pattern="raise",  # Collaborative reasoning with other agents
        context=req_result.data if req_result.success else {}
    )
    
    print(f"✅ Strategic planning completed with {reasoning_result.confidence:.1%} confidence")
    print(f"🧠 Reasoning steps: {len(reasoning_result.steps)}")
    print(f"📈 Final answer: {reasoning_result.final_answer[:100]}...")
    print()
    
    # Phase 3: Architecture and Development
    print("⚙️ Phase 3: Development Workflow Coordination")
    
    # Program Manager coordinates the overall workflow
    coordination_task = AgentTask(
        type="coordinate_development",
        project_phase="architecture_and_development",
        team_members=list(agents.keys()),
        priorities=["core_services", "user_interface", "payment_integration", "testing"],
        context={
            "requirements": req_result.data if req_result.success else {},
            "planning": reasoning_result.final_answer
        }
    )
    
    coordination_result = await agents['manager'].execute(coordination_task)
    print(f"✅ Development coordination: {coordination_result.success}")
    
    if coordination_result.success:
        # Extract tasks and assign to appropriate agents
        tasks = coordination_result.data.get('tasks', [])
        print(f"📋 Generated {len(tasks)} development tasks")
        
        # Demonstrate parallel execution of development tasks
        development_results = []
        
        for i, task_desc in enumerate(tasks[:3]):  # Demo first 3 tasks
            print(f"\n🔨 Executing Task {i+1}: {task_desc[:50]}...")
            
            # Code generation task
            code_task = AgentTask(
                type="generate_code",
                requirements=task_desc,
                language="python",
                framework="fastapi",
                include_tests=True,
                style="clean"
            )
            
            code_result = await agents['developer'].execute(code_task)
            if code_result.success:
                print(f"✅ Code generated: {len(code_result.data.get('code', ''))} characters")
                
                # Automated testing
                test_task = AgentTask(
                    type="generate_tests",
                    code=code_result.data.get('code', ''),
                    test_framework="pytest",
                    coverage_target=90
                )
                
                test_result = await agents['tester'].execute(test_task)
                if test_result.success:
                    print(f"✅ Tests generated: {test_result.data.get('test_count', 0)} test cases")
                
                development_results.append({
                    'task': task_desc,
                    'code_result': code_result,
                    'test_result': test_result
                })
    
    print()
    
    # Phase 4: Tool Integration Demo
    print("🔧 Phase 4: Tool Integration and Discovery")
    
    # Discover available tools
    available_tools = tool_manager.registry.list_tools()
    print(f"🛠️ Available tools: {len(available_tools)}")
    
    # Demonstrate tool recommendation
    recommendations = tool_manager.recommend_tools("data analysis", category="analysis")
    print(f"💡 Recommended data analysis tools: {len(recommendations)}")
    
    # Execute a tool
    if available_tools:
        tool_name = available_tools[0]
        try:
            tool_result = await tool_manager.execute_tool(
                tool_name, 
                {"operation": "test", "data": "sample"},
                agent_id="demo"
            )
            print(f"✅ Tool execution successful: {tool_result.success}")
        except Exception as e:
            print(f"⚠️ Tool execution demo (expected in test env): {str(e)[:50]}")
    print()
    
    # Phase 5: Memory and Learning
    print("🧠 Phase 5: Memory Storage and Experience Learning")
    
    # Store workflow experience
    workflow_summary = {
        "project": "E-commerce Platform Development",
        "phases_completed": ["requirements", "planning", "development", "testing"],
        "agents_involved": list(agents.keys()),
        "reasoning_confidence": reasoning_result.confidence,
        "development_tasks": len(development_results),
        "timestamp": datetime.now().isoformat()
    }
    
    memory_result = await memory_manager.store(
        content=f"Production workflow demonstration: {json.dumps(workflow_summary)}",
        memory_type="LONG_TERM",
        metadata={
            "workflow_type": "production_demo",
            "success": True,
            "agents_count": len(agents)
        }
    )
    
    print(f"✅ Workflow experience stored: {memory_result.success}")
    print()
    
    # Summary and Insights
    print("📊 WORKFLOW COMPLETION SUMMARY")
    print("=" * 50)
    print(f"🎯 Project: E-commerce Platform Development")
    print(f"🤖 Agents Utilized: {len(agents)}")
    print(f"🧠 Reasoning Confidence: {reasoning_result.confidence:.1%}")
    print(f"⚙️ Development Tasks: {len(development_results)}")
    print(f"🛠️ Tools Available: {len(available_tools)}")
    print(f"💾 Memory Storage: {'✅ Success' if memory_result.success else '❌ Failed'}")
    print()
    
    print("🎉 Production workflow demonstration completed successfully!")
    print("📚 This demo showcased:")
    print("   • Multi-agent coordination and communication")
    print("   • Advanced reasoning patterns (RAISE)")
    print("   • Tool integration and discovery")
    print("   • Memory management and learning")
    print("   • Production-ready workflow orchestration")
    
    return {
        'agents': agents,
        'reasoning_result': reasoning_result,
        'development_results': development_results,
        'workflow_summary': workflow_summary
    }


async def main():
    """Main demonstration function."""
    try:
        result = await demonstrate_production_workflow()
        return result
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Starting Production Workflow Demonstration...")
    print(f"Available agent types: {get_available_agent_types()}")
    print()
    
    result = asyncio.run(main())
    if result:
        print("\n✅ Demonstration completed successfully!")
    else:
        print("\n❌ Demonstration failed!")