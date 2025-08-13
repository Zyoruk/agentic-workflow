#!/usr/bin/env python3
"""
Requirement Engineering Agent Demo

This example demonstrates the comprehensive capabilities of the Requirement Engineering Agent
for automated requirement gathering, analysis, validation, and documentation.

The demo showcases:
1. Stakeholder requirement gathering
2. Requirement analysis and quality assessment
3. Requirement validation and consistency checking
4. Comprehensive documentation generation
5. Requirement prioritization and feasibility assessment

Usage:
    python requirement_engineering_demo.py
"""

import asyncio
import json
from datetime import UTC, datetime

from agentic_workflow.agents.requirement_engineering import RequirementEngineeringAgent
from agentic_workflow.agents.base import AgentTask


def print_header(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_subheader(title: str) -> None:
    """Print formatted subsection header."""
    print(f"\n{'-' * 40}")
    print(f" {title}")
    print(f"{'-' * 40}")


async def demonstrate_requirement_gathering():
    """Demonstrate requirement gathering capabilities."""
    print_header("🔍 REQUIREMENT GATHERING DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    # E-commerce platform requirements
    task = AgentTask(
        operation="gather",
        context={
            "domain": "e-commerce",
            "project_id": "ecommerce-platform-v2",
            "project_title": "Next-Generation E-commerce Platform",
            "business_goals": [
                "Increase conversion rate by 25%",
                "Reduce cart abandonment by 30%",
                "Support 10x current traffic",
                "Mobile-first user experience"
            ],
            "target_users": ["customers", "merchants", "administrators"],
            "integration_requirements": ["payment_gateways", "inventory_systems", "analytics"],
        },
        stakeholders=[
            "product_manager",
            "ux_designer", 
            "lead_developer",
            "business_analyst",
            "customers",
            "merchants"
        ],
        constraints=[
            "12-month timeline",
            "$500K budget",
            "PCI DSS compliance",
            "GDPR compliance",
            "99.9% uptime requirement"
        ],
        priority="high"
    )
    
    print("📋 Gathering requirements for e-commerce platform...")
    print(f"   Domain: {task.get('context', {}).get('domain')}")
    print(f"   Stakeholders: {', '.join(task.get('stakeholders', []))}")
    print(f"   Constraints: {len(task.get('constraints', []))} major constraints")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        print(f"\n✅ Successfully gathered {data['total_requirements']} requirements")
        print(f"   Stakeholders consulted: {', '.join(data['stakeholders_consulted'])}")
        print(f"   Gathering method: {data['gathering_method']}")
        
        print("\n📄 Sample Requirements:")
        for i, req in enumerate(data['requirements'][:3], 1):
            print(f"   {i}. {req['id']}: {req['title']}")
            print(f"      Type: {req['type']} | Priority: {req['priority']}")
            print(f"      Description: {req['description']}")
            if req.get('acceptance_criteria'):
                print(f"      Acceptance Criteria: {req['acceptance_criteria'][0]}")
            print()
        
        if len(data['requirements']) > 3:
            print(f"   ... and {len(data['requirements']) - 3} more requirements")
        
        return data['requirements']
    else:
        print(f"❌ Error: {result.error}")
        return []


async def demonstrate_requirement_analysis():
    """Demonstrate requirement analysis capabilities."""
    print_header("📊 REQUIREMENT ANALYSIS DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    task = AgentTask(
        operation="analyze",
        context={
            "project_id": "ecommerce-platform-v2",
            "analysis_scope": "comprehensive",
            "quality_criteria": ["completeness", "consistency", "feasibility", "testability"]
        }
    )
    
    print("🔍 Analyzing requirement quality and completeness...")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        print(f"\n✅ Analysis complete for {data['total_requirements']} requirements")
        
        print("\n📈 Requirements by Type:")
        for req_type, count in data['by_type'].items():
            print(f"   {req_type.title()}: {count} requirements")
        
        print("\n🎯 Requirements by Priority:")
        for priority, count in data['by_priority'].items():
            print(f"   {priority.title()}: {count} requirements")
        
        print(f"\n📋 Completeness Score: {data['completeness_score']:.1f}%")
        
        if data['quality_issues']:
            print(f"\n⚠️  Quality Issues Found: {len(data['quality_issues'])}")
            for i, issue in enumerate(data['quality_issues'][:3], 1):
                print(f"   {i}. {issue}")
            if len(data['quality_issues']) > 3:
                print(f"   ... and {len(data['quality_issues']) - 3} more issues")
        
        print(f"\n💡 Recommendations: {len(data['recommendations'])}")
        for i, rec in enumerate(data['recommendations'][:3], 1):
            print(f"   {i}. {rec}")
        
        return data
    else:
        print(f"❌ Error: {result.error}")
        return {}


async def demonstrate_requirement_validation():
    """Demonstrate requirement validation capabilities."""
    print_header("✅ REQUIREMENT VALIDATION DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    task = AgentTask(
        operation="validate",
        context={
            "project_id": "ecommerce-platform-v2",
            "validation_rules": [
                "completeness",
                "consistency", 
                "feasibility",
                "testability",
                "traceability"
            ]
        }
    )
    
    print("🔍 Validating requirements for consistency and quality...")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        total_reqs = data['valid_requirements'] + data['invalid_requirements']
        
        print(f"\n✅ Validation complete for {total_reqs} requirements")
        if total_reqs > 0:
            print(f"   Valid: {data['valid_requirements']} ({data['valid_requirements']/total_reqs*100:.1f}%)")
            print(f"   Invalid: {data['invalid_requirements']} ({data['invalid_requirements']/total_reqs*100:.1f}%)")
        else:
            print(f"   Valid: {data['valid_requirements']}")
            print(f"   Invalid: {data['invalid_requirements']}")
        
        if data['errors']:
            print(f"\n❌ Validation Errors: {len(data['errors'])}")
            for i, error in enumerate(data['errors'][:3], 1):
                print(f"   {i}. {error}")
            if len(data['errors']) > 3:
                print(f"   ... and {len(data['errors']) - 3} more errors")
        
        if data['warnings']:
            print(f"\n⚠️  Validation Warnings: {len(data['warnings'])}")
            for i, warning in enumerate(data['warnings'][:3], 1):
                print(f"   {i}. {warning}")
        
        print(f"\n📋 Detailed Validation Results: {len(data['validation_details'])} requirements processed")
        
        return data
    else:
        print(f"❌ Error: {result.error}")
        return {}


async def demonstrate_requirement_documentation():
    """Demonstrate requirement documentation generation."""
    print_header("📚 REQUIREMENT DOCUMENTATION DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    task = AgentTask(
        operation="document",
        context={
            "project_id": "ecommerce-platform-v2",
            "project_title": "Next-Generation E-commerce Platform - Requirements Specification",
            "document_type": "SRS",
            "template": "IEEE_830",
            "assumptions": [
                "Third-party payment processors will maintain 99.9% uptime",
                "Current user base will migrate to new platform within 6 months",
                "Existing product catalog will be imported automatically"
            ]
        },
        stakeholders=[
            "product_manager",
            "technical_lead",
            "qa_manager",
            "business_analyst"
        ],
        constraints=[
            "Must comply with PCI DSS standards",
            "GDPR compliance required for EU users",
            "Accessibility standards (WCAG 2.1 AA) must be met",
            "Mobile responsiveness required"
        ]
    )
    
    print("📝 Generating comprehensive requirement documentation...")
    print(f"   Document type: {task.get('context', {}).get('document_type')}")
    print(f"   Template: {task.get('context', {}).get('template')}")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        document = data['document']
        
        print(f"\n✅ Documentation generated successfully")
        print(f"   Document title: {document['title']}")
        print(f"   Version: {document['version']}")
        print(f"   Requirements included: {len(document['requirements'])}")
        print(f"   Stakeholders: {len(document['stakeholders'])}")
        print(f"   Format: {data['format']}")
        
        print("\n📄 Document Structure:")
        print("   1. Project Overview")
        print("   2. Stakeholder Information")
        print("   3. Functional Requirements")
        print("   4. Non-Functional Requirements")
        print("   5. Constraints and Assumptions")
        print("   6. Glossary")
        
        # Show a sample of the formatted document
        formatted_sample = data['formatted_document'][:500]
        print(f"\n📋 Document Preview (first 500 characters):")
        print("─" * 50)
        print(formatted_sample)
        if len(data['formatted_document']) > 500:
            print("\n... (truncated)")
        print("─" * 50)
        
        return data
    else:
        print(f"❌ Error: {result.error}")
        return {}


async def demonstrate_requirement_prioritization():
    """Demonstrate requirement prioritization capabilities."""
    print_header("🎯 REQUIREMENT PRIORITIZATION DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    task = AgentTask(
        operation="prioritize",
        context={
            "project_id": "ecommerce-platform-v2",
            "prioritization_method": "business_value_effort_matrix",
            "business_factors": {
                "revenue_impact": 0.4,
                "user_satisfaction": 0.3,
                "competitive_advantage": 0.2,
                "regulatory_compliance": 0.1
            },
            "effort_factors": {
                "development_complexity": 0.5,
                "resource_requirements": 0.3,
                "timeline_impact": 0.2
            }
        }
    )
    
    print("🎯 Prioritizing requirements based on business value and effort...")
    print("   Method: Business Value vs Effort Matrix")
    print("   Factors: Revenue impact, user satisfaction, complexity, resources")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        
        print(f"\n✅ Prioritization complete for {len(data['prioritized_requirements'])} requirements")
        print(f"   Method used: {data['prioritization_method']}")
        
        print("\n📊 Priority Distribution:")
        print(f"   High Priority: {data['high_priority_count']} requirements")
        print(f"   Medium Priority: {data['medium_priority_count']} requirements") 
        print(f"   Low Priority: {data['low_priority_count']} requirements")
        
        print("\n🏆 Top 5 Prioritized Requirements:")
        for i, req in enumerate(data['prioritized_requirements'][:5], 1):
            priority_score = req.get('priority_score', 0)
            print(f"   {i}. {req.get('id', 'N/A')}: {req.get('title', 'No title')}")
            print(f"      Priority: {req.get('priority', 'unknown')} (Score: {priority_score:.1f})")
            print(f"      Type: {req.get('type', 'unknown')}")
            print()
        
        return data
    else:
        print(f"❌ Error: {result.error}")
        return {}


async def demonstrate_feasibility_assessment():
    """Demonstrate feasibility assessment capabilities."""
    print_header("🔍 FEASIBILITY ASSESSMENT DEMONSTRATION")
    
    agent = RequirementEngineeringAgent()
    
    task = AgentTask(
        operation="assess_feasibility",
        context={
            "project_id": "ecommerce-platform-v2",
            "assessment_criteria": [
                "technical_feasibility",
                "resource_feasibility", 
                "timeline_feasibility",
                "budget_feasibility"
            ],
            "constraints": {
                "budget": 500000,
                "timeline_months": 12,
                "team_size": 8,
                "technology_stack": ["Python", "React", "PostgreSQL", "Redis", "AWS"]
            }
        }
    )
    
    print("🔍 Assessing requirement feasibility...")
    print("   Criteria: Technical, resource, timeline, and budget feasibility")
    print("   Constraints: $500K budget, 12-month timeline, 8-person team")
    
    result = await agent.execute(task)
    
    if result.success:
        data = result.data
        
        print(f"\n✅ Feasibility assessment complete")
        print(f"   Overall Feasibility: {data['overall_feasibility'].title()}")
        print(f"   Technical Feasibility: {data['technical_feasibility'].title()}")
        print(f"   Resource Feasibility: {data['resource_feasibility'].title()}")
        print(f"   Timeline Feasibility: {data['timeline_feasibility'].title()}")
        
        if data['risk_factors']:
            print(f"\n⚠️  Risk Factors: {len(data['risk_factors'])}")
            for i, risk in enumerate(data['risk_factors'][:3], 1):
                print(f"   {i}. {risk}")
        
        if data['recommendations']:
            print(f"\n💡 Recommendations: {len(data['recommendations'])}")
            for i, rec in enumerate(data['recommendations'][:3], 1):
                print(f"   {i}. {rec}")
        
        print(f"\n📋 Individual Requirement Assessments: {len(data['requirement_assessments'])}")
        
        return data
    else:
        print(f"❌ Error: {result.error}")
        return {}


async def demonstrate_agent_capabilities():
    """Demonstrate agent capabilities and metadata."""
    print_header("🤖 REQUIREMENT ENGINEERING AGENT CAPABILITIES")
    
    agent = RequirementEngineeringAgent()
    
    print("🔧 Agent Configuration:")
    print(f"   Name: {agent.name}")
    print(f"   Type: Requirement Engineering Agent")
    print(f"   Capabilities: {len(agent.capabilities)}")
    
    print("\n🎯 Core Capabilities:")
    for i, capability in enumerate(agent.capabilities, 1):
        # Convert snake_case to Title Case
        formatted_capability = capability.replace('_', ' ').title()
        print(f"   {i}. {formatted_capability}")
    
    print("\n📋 Supported Operations:")
    operations = [
        ("gather", "Collect requirements from stakeholders and context"),
        ("analyze", "Analyze requirement quality and completeness"),
        ("validate", "Validate requirements for consistency and feasibility"),
        ("document", "Generate comprehensive requirement documentation"),
        ("prioritize", "Prioritize requirements based on business value"),
        ("assess_feasibility", "Assess technical and business feasibility")
    ]
    
    for i, (op, desc) in enumerate(operations, 1):
        print(f"   {i}. {op}: {desc}")
    
    print("\n🔗 Integration Points:")
    integrations = [
        "Memory System (Neo4j, Redis, Weaviate)",
        "LangChain for NLP processing",
        "Agent Framework for workflow coordination",
        "Graph Database for requirement relationships",
        "Vector Storage for semantic search"
    ]
    
    for i, integration in enumerate(integrations, 1):
        print(f"   {i}. {integration}")


async def main():
    """Run the complete Requirement Engineering Agent demonstration."""
    print_header("🚀 REQUIREMENT ENGINEERING AGENT DEMONSTRATION")
    print("Welcome to the comprehensive Requirement Engineering Agent demo!")
    print("This demonstration showcases automated requirement engineering capabilities.")
    
    try:
        # Show agent capabilities
        await demonstrate_agent_capabilities()
        
        # Step 1: Gather requirements
        requirements = await demonstrate_requirement_gathering()
        
        # Step 2: Analyze requirements
        analysis = await demonstrate_requirement_analysis()
        
        # Step 3: Validate requirements
        validation = await demonstrate_requirement_validation()
        
        # Step 4: Generate documentation
        documentation = await demonstrate_requirement_documentation()
        
        # Step 5: Prioritize requirements
        prioritization = await demonstrate_requirement_prioritization()
        
        # Step 6: Assess feasibility
        feasibility = await demonstrate_feasibility_assessment()
        
        print_header("📊 DEMONSTRATION SUMMARY")
        print("✅ Successfully demonstrated all Requirement Engineering Agent capabilities:")
        print("   1. ✅ Requirement gathering from stakeholders and context")
        print("   2. ✅ Requirement analysis and quality assessment")
        print("   3. ✅ Requirement validation and consistency checking")
        print("   4. ✅ Comprehensive documentation generation")
        print("   5. ✅ Intelligent requirement prioritization")
        print("   6. ✅ Feasibility assessment and risk analysis")
        
        print("\n🎯 Key Benefits Demonstrated:")
        benefits = [
            "Automated stakeholder requirement gathering",
            "Intelligent requirement analysis and quality scoring",
            "Comprehensive validation with error detection",
            "Professional documentation generation",
            "Data-driven prioritization using business value metrics",
            "Risk assessment and feasibility analysis",
            "Integration with enterprise workflow systems"
        ]
        
        for i, benefit in enumerate(benefits, 1):
            print(f"   {i}. {benefit}")
        
        print("\n🚀 Next Steps:")
        print("   • Integrate with your project management tools")
        print("   • Customize requirement templates for your domain")
        print("   • Set up automated requirement tracking workflows")
        print("   • Configure stakeholder notification systems")
        print("   • Implement requirement traceability matrices")
        
        print(f"\n{'=' * 60}")
        print(" Requirement Engineering Agent Demo Complete! ")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())