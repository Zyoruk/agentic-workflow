#!/usr/bin/env python3
"""Demonstration of Program Manager Agent capabilities.

This script shows how to use the Program Manager Agent to:
1. Create and manage comprehensive software projects
2. Allocate and optimize resources across multiple agents
3. Track progress and milestones
4. Assess and mitigate project risks
5. Coordinate multiple agents for complex workflows
6. Generate comprehensive reports for stakeholders
7. Manage timelines and optimize project schedules
8. Plan strategic project initiatives
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.program_manager import ProgramManagerAgent


async def demonstrate_program_manager_agent():
    """Demonstrate Program Manager Agent capabilities with comprehensive examples."""

    # Initialize the Program Manager Agent
    config = {
        "max_concurrent_projects": 10,
        "default_risk_tolerance": "medium",
        "budget_alert_threshold": 0.8,
        "available_agents": ["code_generation", "testing", "review", "cicd", "planning"],
        "max_agent_utilization": 0.8,
        "detailed_reporting": True,
        "stakeholder_update_frequency": "weekly",
    }

    pm_agent = ProgramManagerAgent(config=config)
    await pm_agent.initialize()

    print("🏢 Program Manager Agent Demo - Enterprise Project Management")
    print("=" * 70)

    # Demo 1: Create Comprehensive Software Project
    print("\n1️⃣ Creating Enterprise Software Project")
    print("-" * 42)

    project_config = {
        "name": "AI-Powered Customer Analytics Platform",
        "description": "Develop a comprehensive AI-driven analytics platform for customer insights",
        "objectives": [
            "Build scalable microservices architecture",
            "Implement real-time data processing",
            "Deploy ML models for customer segmentation",
            "Ensure 99.9% uptime and security compliance",
            "Deliver within 8-week timeline and $50K budget"
        ],
        "timeline": {
            "duration_weeks": 8,
            "buffer_percentage": 0.15,
        },
        "budget": 50000.0,
        "stakeholders": [
            "CTO", "Product Manager", "Data Science Team",
            "Engineering Team", "QA Team", "DevOps Team"
        ],
        "risk_tolerance": "medium",
    }

    create_project_task = AgentTask(
        task_id="demo_project_creation",
        type="create_project",
        prompt="Create enterprise AI analytics platform project",
        context={
            "project_config": project_config,
            "project_scope": "full",
        },
    )

    project_result = await pm_agent.execute(create_project_task)

    if project_result.success:
        project_id = project_result.data["project_id"]
        print(f"✅ Project created successfully")
        print(f"🆔 Project ID: {project_id}")
        print(f"📋 Tasks: {project_result.data['tasks_count']}")
        print(f"🎯 Milestones: {project_result.data['milestones_count']}")
        print(f"⏱️  Estimated Duration: {project_result.data['estimated_duration']:.1f} hours")
        print(f"💰 Estimated Cost: ${project_result.data['estimated_cost']:,.2f}")

        # Show project structure
        project = pm_agent.active_projects[project_id]
        print(f"\n📊 Project Structure:")
        print(f"   Status: {project.status.value}")
        print(f"   Budget: ${project.config.budget:,.2f}")
        print(f"   Risk Tolerance: {project.config.risk_tolerance}")
        print(f"   Stakeholders: {len(project.config.stakeholders)}")
    else:
        print("❌ Project creation failed")
        return

    # Demo 2: Resource Allocation and Optimization
    print("\n2️⃣ Resource Allocation and Optimization")
    print("-" * 43)

    # Initial resource allocation
    allocation_task = AgentTask(
        task_id="demo_resource_allocation",
        type="allocate_resources",
        prompt="Allocate resources for AI analytics platform",
        context={
            "allocation_type": "initial",
            "project_id": project_id,
            "resource_requirements": {
                "priority_agents": ["code_generation", "testing", "cicd"],
                "compute_intensive": True,
                "parallel_execution": True,
            },
        },
    )

    allocation_result = await pm_agent.execute(allocation_task)

    if allocation_result.success:
        print(f"✅ Initial resource allocation completed")
        allocation_data = allocation_result.data["allocation_result"]
        print(f"💰 Total Cost: ${allocation_data['total_cost']:,.2f}")
        print(f"🔧 Resources Allocated: {len(allocation_data['allocated_resources'])}")

        # Show resource utilization
        utilization = allocation_result.data["resource_utilization"]
        print(f"\n📊 Resource Utilization:")
        for resource_id, util_data in list(utilization.items())[:5]:
            print(f"   {resource_id}: {util_data['utilization_percentage']:.1f}% ({util_data['type']})")

    # Optimize resource allocation
    optimization_task = AgentTask(
        task_id="demo_resource_optimization",
        type="allocate_resources",
        prompt="Optimize resource allocation for efficiency",
        context={
            "allocation_type": "optimization",
            "project_id": project_id,
        },
    )

    optimization_result = await pm_agent.execute(optimization_task)

    if optimization_result.success:
        opt_data = optimization_result.data["allocation_result"]["optimization_results"]
        print(f"\n🚀 Resource Optimization Results:")
        print(f"   Efficiency Gain: {opt_data['efficiency_gain']:.1f}%")
        print(f"   Cost Reduction: {opt_data['cost_reduction']:.1f}%")
        print(f"   Time Savings: {opt_data['time_savings']:.1f}%")
        print(f"   Recommendations: {len(opt_data['recommendations'])}")

    # Demo 3: Progress Tracking and Milestone Management
    print("\n3️⃣ Progress Tracking and Milestone Management")
    print("-" * 48)

    # Update project progress
    update_task = AgentTask(
        task_id="demo_project_update",
        type="manage_project",
        prompt="Update project progress",
        context={
            "project_id": project_id,
            "action": "update",
            "updates": {
                "progress_percentage": 35.0,
                "budget_used": 15000.0,
                "task_updates": [
                    {
                        "task_id": "task_planning",
                        "status": "completed",
                        "completion_percentage": 100.0,
                        "actual_hours": 12.0,
                    },
                    {
                        "task_id": "task_development",
                        "status": "in_progress",
                        "completion_percentage": 45.0,
                        "actual_hours": 25.0,
                    }
                ],
            },
        },
    )

    update_result = await pm_agent.execute(update_task)

    if update_result.success:
        print(f"✅ Project progress updated")
        print(f"📈 Progress: 35.0%")
        print(f"💰 Budget Used: $15,000 / $50,000")

    # Track project progress
    progress_task = AgentTask(
        task_id="demo_progress_tracking",
        type="track_progress",
        prompt="Track comprehensive project progress",
        context={
            "tracking_type": "project",
            "project_id": project_id,
        },
    )

    progress_result = await pm_agent.execute(progress_task)

    if progress_result.success:
        progress_data = progress_result.data["progress_result"]
        print(f"\n📊 Progress Tracking Results:")
        print(f"   Overall Progress: {progress_data['progress_percentage']:.1f}%")
        print(f"   Completed Tasks: {progress_data['completed_tasks']}/{progress_data['total_tasks']}")
        print(f"   On Schedule: {'✅ Yes' if progress_data['on_schedule'] else '⚠️  Behind'}")

    # Track milestone progress
    milestone_task = AgentTask(
        task_id="demo_milestone_tracking",
        type="track_progress",
        prompt="Track milestone progress",
        context={
            "tracking_type": "milestone",
            "project_id": project_id,
        },
    )

    milestone_result = await pm_agent.execute(milestone_task)

    if milestone_result.success:
        milestone_data = milestone_result.data["progress_result"]
        print(f"\n🎯 Milestone Progress:")
        print(f"   Total Milestones: {milestone_data['total_milestones']}")
        print(f"   Completed: {milestone_data['milestones_completed']}")

        for milestone in milestone_data["milestone_status"][:3]:
            status_icon = "✅" if milestone["completion_percentage"] == 100 else "🔄"
            print(f"   {status_icon} {milestone['name']}: {milestone['completion_percentage']:.0f}%")

    # Demo 4: Risk Assessment and Management
    print("\n4️⃣ Risk Assessment and Management")
    print("-" * 36)

    # Assess current risks
    risk_assess_task = AgentTask(
        task_id="demo_risk_assessment",
        type="manage_risks",
        prompt="Assess current project risks",
        context={
            "project_id": project_id,
            "risk_action": "assess",
        },
    )

    risk_result = await pm_agent.execute(risk_assess_task)

    if risk_result.success:
        risk_data = risk_result.data["risk_result"]
        print(f"🔍 Risk Assessment Results:")
        print(f"   Total Risks: {risk_data['risk_count']}")
        print(f"   High Priority: {risk_data['high_priority_risks']}")

        print(f"\n⚠️  Current Risks:")
        for risk in risk_data["current_risks"][:3]:
            impact_icon = "🔴" if risk["impact"] == "high" else "🟡" if risk["impact"] == "medium" else "🟢"
            print(f"   {impact_icon} {risk['category']}: {risk['description']}")
            print(f"      Probability: {risk['probability']} | Impact: {risk['impact']}")
            print(f"      Mitigation: {risk['mitigation']}")

    # Mitigate a risk
    if risk_data["current_risks"]:
        risk_id = risk_data["current_risks"][0]["risk_id"]
        mitigate_task = AgentTask(
            task_id="demo_risk_mitigation",
            type="manage_risks",
            prompt="Mitigate identified risk",
            context={
                "project_id": project_id,
                "risk_action": "mitigate",
                "risk_id": risk_id,
            },
        )

        mitigate_result = await pm_agent.execute(mitigate_task)

        if mitigate_result.success:
            print(f"\n✅ Risk mitigation implemented for: {risk_id}")

    # Demo 5: Agent Coordination and Workflow Orchestration
    print("\n5️⃣ Agent Coordination and Workflow Orchestration")
    print("-" * 52)

    # Setup agent coordination
    coord_setup_task = AgentTask(
        task_id="demo_agent_coordination",
        type="coordinate_agents",
        prompt="Setup multi-agent coordination workflow",
        context={
            "coordination_type": "setup",
            "project_id": project_id,
        },
    )

    coord_result = await pm_agent.execute(coord_setup_task)

    if coord_result.success:
        coord_data = coord_result.data["coordination_result"]["coordination_plan"]
        print(f"🤝 Agent Coordination Setup:")
        print(f"   Agents Involved: {len(coord_data['agents_involved'])}")
        print(f"   Strategy: {coord_data['coordination_strategy']}")
        print(f"   Protocol: {coord_data['communication_protocol']}")
        print(f"   Handoff Points: {len(coord_data['handoff_points'])}")

        print(f"\n🔄 Agent Workflow:")
        for agent in coord_data["agents_involved"]:
            print(f"   • {agent.replace('_', ' ').title()}")

    # Monitor agent coordination
    coord_monitor_task = AgentTask(
        task_id="demo_coordination_monitoring",
        type="coordinate_agents",
        prompt="Monitor agent coordination performance",
        context={
            "coordination_type": "monitor",
            "project_id": project_id,
        },
    )

    monitor_result = await pm_agent.execute(coord_monitor_task)

    if monitor_result.success:
        monitor_data = monitor_result.data["coordination_result"]["monitoring_data"]
        print(f"\n📊 Coordination Monitoring:")
        print(f"   Health: {monitor_data['coordination_health']}")
        print(f"   Handoff Efficiency: {monitor_data['performance_metrics']['handoff_efficiency']:.1%}")
        print(f"   Coordination Overhead: {monitor_data['performance_metrics']['coordination_overhead']:.1%}")

        print(f"\n🎯 Agent Utilization:")
        for agent, utilization in monitor_data["agent_utilization"].items():
            bar_length = int(utilization * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"   {agent.replace('_', ' ').title():<15} {bar} {utilization:.1%}")

    # Demo 6: Comprehensive Reporting
    print("\n6️⃣ Comprehensive Project Reporting")
    print("-" * 37)

    # Generate status report
    status_report_task = AgentTask(
        task_id="demo_status_report",
        type="generate_report",
        prompt="Generate comprehensive status report",
        context={
            "report_type": "status",
            "project_id": project_id,
        },
    )

    status_result = await pm_agent.execute(status_report_task)

    if status_result.success:
        report = status_result.data["report"]["report"]
        print(f"📋 Project Status Report:")
        print(f"   Project: {report['project_name']}")
        print(f"   Status: {report['status']}")
        print(f"   Progress: {report['progress_percentage']:.1f}%")

        budget = report["budget_status"]
        print(f"\n💰 Budget Status:")
        print(f"   Allocated: ${budget['allocated']:,.2f}")
        print(f"   Used: ${budget['used']:,.2f}")
        print(f"   Remaining: ${budget['remaining']:,.2f}")

        tasks = report["task_summary"]
        print(f"\n📋 Task Summary:")
        print(f"   Total: {tasks['total']} | Completed: {tasks['completed']}")
        print(f"   In Progress: {tasks['in_progress']} | Pending: {tasks['pending']}")

    # Generate executive report
    exec_report_task = AgentTask(
        task_id="demo_executive_report",
        type="generate_report",
        prompt="Generate executive summary report",
        context={"report_type": "executive"},
    )

    exec_result = await pm_agent.execute(exec_report_task)

    if exec_result.success:
        exec_report = exec_result.data["report"]["report"]
        summary = exec_report["executive_summary"]

        print(f"\n🏢 Executive Summary:")
        print(f"   Total Projects: {summary['total_projects']}")
        print(f"   Overall Health: {summary['overall_health']}")

        print(f"\n🎯 Key Achievements:")
        for achievement in summary["key_achievements"]:
            print(f"   ✅ {achievement}")

        print(f"\n⚠️  Key Challenges:")
        for challenge in summary["key_challenges"]:
            print(f"   🔴 {challenge}")

        financial = exec_report["financial_summary"]
        print(f"\n💰 Financial Summary:")
        print(f"   Budget Efficiency: {financial['budget_efficiency']:.1%}")
        print(f"   Cost Savings: {financial['cost_savings']:.1f}%")

    # Demo 7: Timeline Management and Optimization
    print("\n7️⃣ Timeline Management and Optimization")
    print("-" * 43)

    # Optimize timeline
    timeline_optimize_task = AgentTask(
        task_id="demo_timeline_optimization",
        type="manage_timeline",
        prompt="Optimize project timeline for efficiency",
        context={
            "project_id": project_id,
            "timeline_action": "optimize",
        },
    )

    timeline_result = await pm_agent.execute(timeline_optimize_task)

    if timeline_result.success:
        timeline_data = timeline_result.data["timeline_result"]["optimization_results"]
        print(f"⚡ Timeline Optimization:")
        print(f"   Original Duration: {timeline_data['original_duration']:.1f} hours")
        print(f"   Optimized Duration: {timeline_data['optimized_duration']:.1f} hours")
        print(f"   Time Savings: {timeline_data['time_savings']:.1f}%")
        print(f"   Quality Impact: {timeline_data['impact_on_quality']}")
        print(f"   Cost Impact: {timeline_data['impact_on_cost']}")

        print(f"\n🚀 Optimization Strategies:")
        for strategy in timeline_data["optimization_strategies"]:
            print(f"   • {strategy}")

    # Validate timeline
    timeline_validate_task = AgentTask(
        task_id="demo_timeline_validation",
        type="manage_timeline",
        prompt="Validate project timeline feasibility",
        context={
            "project_id": project_id,
            "timeline_action": "validate",
        },
    )

    validate_result = await pm_agent.execute(timeline_validate_task)

    if validate_result.success:
        validation = validate_result.data["timeline_result"]["validation_results"]
        print(f"\n✅ Timeline Validation:")
        print(f"   Feasible: {'✅ Yes' if validation['timeline_feasible'] else '❌ No'}")
        print(f"   Confidence: {validation['confidence_level']:.1%}")
        print(f"   Critical Path: {validation['critical_path_duration']:.1f} hours")
        print(f"   Resource Conflicts: {validation['resource_conflicts']}")

    # Demo 8: Strategic Planning Capabilities
    print("\n8️⃣ Strategic Planning Capabilities")
    print("-" * 36)

    # Plan new project
    objective = "Launch AI-powered customer service chatbot with 24/7 support"
    tasks = await pm_agent.plan(objective)

    print(f"📋 Strategic Plan for: '{objective}'")
    print(f"   Generated {len(tasks)} strategic tasks")
    print()

    total_duration = 0
    for i, task in enumerate(tasks, 1):
        duration = task.get('estimated_duration', 1.0)
        total_duration += duration
        deps = task.get('dependencies', [])

        print(f"   {i}. {task.get('type', 'unknown').replace('_', ' ').title()}")
        print(f"      ⏱️  Duration: {duration}h | Priority: {task.get('priority', 'medium')}")
        if deps:
            print(f"      🔗 Dependencies: {', '.join(deps)}")
        print()

    print(f"📊 Strategic Plan Summary:")
    print(f"   Total Duration: {total_duration} hours")
    print(f"   Parallel Opportunities: {len([t for t in tasks if not t.get('dependencies')])}")

    # Demo 9: Overall Program Status
    print("\n9️⃣ Overall Program Status")
    print("-" * 28)

    # Track overall progress
    overall_task = AgentTask(
        task_id="demo_overall_tracking",
        type="track_progress",
        prompt="Track overall program progress",
        context={"tracking_type": "overall"},
    )

    overall_result = await pm_agent.execute(overall_task)

    if overall_result.success:
        overall_data = overall_result.data["progress_result"]
        stats = overall_data["statistics"]

        print(f"🏢 Program Overview:")
        print(f"   Active Projects: {stats['total_projects']}")
        print(f"   Overall Progress: {overall_data['overall_progress_percentage']:.1f}%")
        print(f"   Total Tasks: {stats['total_tasks']}")
        print(f"   Completed Tasks: {stats['completed_tasks']}")
        print(f"   Total Budget: ${stats['total_budget']:,.2f}")
        print(f"   Budget Used: ${stats['budget_used']:,.2f}")

        print(f"\n📊 Projects by Status:")
        for status, count in stats["projects_by_status"].items():
            print(f"   {status.replace('_', ' ').title()}: {count}")

    # Demo 10: Agent Capabilities Summary
    print("\n🔟 Program Manager Capabilities")
    print("-" * 34)

    capabilities = pm_agent.get_capabilities()
    print("🛠️  Available capabilities:")
    for i, capability in enumerate(capabilities, 1):
        print(f"   {i:2d}. {capability.replace('_', ' ').title()}")

    print("\n" + "=" * 70)
    print("✨ Program Manager Agent demonstration completed!")
    print("   The agent provides enterprise-grade project management")
    print("   with comprehensive planning, execution, and monitoring.")


async def demonstrate_multi_project_scenario():
    """Demonstrate managing multiple concurrent projects."""

    print("\n" + "=" * 70)
    print("🏭 Multi-Project Management Scenario")
    print("=" * 70)

    # Initialize Program Manager for multi-project scenario
    config = {
        "max_concurrent_projects": 15,
        "default_risk_tolerance": "low",  # Conservative for multiple projects
        "budget_alert_threshold": 0.75,
        "detailed_reporting": True,
    }

    pm_agent = ProgramManagerAgent(config=config)
    await pm_agent.initialize()

    print("\n🎯 Scenario: Managing 3 concurrent enterprise projects")
    print("-" * 55)

    # Create multiple projects
    projects = [
        {
            "name": "Mobile App Redesign",
            "description": "Complete redesign of mobile application",
            "budget": 25000.0,
            "duration_weeks": 6,
        },
        {
            "name": "API Gateway Implementation",
            "description": "Implement enterprise API gateway",
            "budget": 35000.0,
            "duration_weeks": 8,
        },
        {
            "name": "Data Migration Project",
            "description": "Migrate legacy data to cloud platform",
            "budget": 40000.0,
            "duration_weeks": 10,
        },
    ]

    project_ids = []

    for i, project_config in enumerate(projects, 1):
        create_task = AgentTask(
            task_id=f"multi_project_{i}",
            type="create_project",
            prompt=f"Create {project_config['name']}",
            context={
                "project_config": {
                    **project_config,
                    "objectives": ["Deliver on time", "Stay within budget", "Ensure quality"],
                    "timeline": {"duration_weeks": project_config["duration_weeks"]},
                    "stakeholders": ["Project Manager", "Development Team"],
                    "risk_tolerance": "low",
                },
                "project_scope": "standard",
            },
        )

        result = await pm_agent.execute(create_task)
        if result.success:
            project_ids.append(result.data["project_id"])
            print(f"✅ Project {i}: {project_config['name']} created")

    # Generate resource report for all projects
    resource_report_task = AgentTask(
        task_id="multi_project_resources",
        type="generate_report",
        prompt="Generate multi-project resource report",
        context={"report_type": "resource"},
    )

    resource_result = await pm_agent.execute(resource_report_task)

    if resource_result.success:
        resource_report = resource_result.data["report"]["report"]
        utilization = resource_report["utilization_summary"]

        print(f"\n📊 Multi-Project Resource Analysis:")
        print(f"   Total Resources: {resource_report['total_resources']}")
        print(f"   Average Utilization: {utilization['average_utilization']:.1f}%")
        print(f"   Overutilized: {utilization['overutilized_resources']}")
        print(f"   Underutilized: {utilization['underutilized_resources']}")

        print(f"\n💡 Resource Recommendations:")
        for rec in resource_report["recommendations"]:
            print(f"   • {rec}")

    # Track overall program progress
    overall_task = AgentTask(
        task_id="multi_project_overall",
        type="track_progress",
        prompt="Track multi-project program progress",
        context={"tracking_type": "overall"},
    )

    overall_result = await pm_agent.execute(overall_task)

    if overall_result.success:
        overall_data = overall_result.data["progress_result"]
        stats = overall_data["statistics"]

        print(f"\n🏢 Multi-Project Program Status:")
        print(f"   Active Projects: {stats['total_projects']}")
        print(f"   Total Budget: ${stats['total_budget']:,.2f}")
        print(f"   Total Tasks: {stats['total_tasks']}")
        print(f"   Overall Progress: {overall_data['overall_progress_percentage']:.1f}%")

    print("\n💼 Multi-project management scenario completed!")
    print("   Successfully managing enterprise portfolio with")
    print("   optimized resource allocation and risk management.")


if __name__ == "__main__":
    # Run the comprehensive demonstrations
    print("🚀 Starting Program Manager Agent Comprehensive Demo...")

    # Main demonstration
    asyncio.run(demonstrate_program_manager_agent())

    # Multi-project scenario
    asyncio.run(demonstrate_multi_project_scenario())

    print("\n💡 Next steps:")
    print("   1. Integrate with external project management tools")
    print("   2. Set up automated reporting and alerts")
    print("   3. Configure stakeholder notification systems")
    print("   4. Implement predictive analytics for better planning")
