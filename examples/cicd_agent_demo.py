#!/usr/bin/env python3
"""Demonstration of CI/CD Agent capabilities.

This script shows how to use the CI/CD Agent to:
1. Create and manage CI/CD pipelines
2. Deploy applications to different environments
3. Manage deployment environments
4. Perform health checks and monitoring
5. Execute rollback operations
6. Plan comprehensive deployment workflows
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.cicd import CICDAgent


async def demonstrate_cicd_agent():
    """Demonstrate CI/CD Agent capabilities with comprehensive examples."""

    # Initialize the CI/CD Agent
    config = {
        "gitlab_url": "https://gitlab.example.com",
        "gitlab_token": "demo-token-12345",
        "project_id": "agentic-workflow/main",
        "supported_environments": ["development", "staging", "production"],
        "deployment_timeout": 600,
        "auto_rollback_enabled": True,
        "container_registry": "registry.gitlab.com/agentic-workflow",
    }

    cicd_agent = CICDAgent(config=config)
    await cicd_agent.initialize()

    print("🚀 CI/CD Agent Demo - Comprehensive Deployment Automation")
    print("=" * 65)

    # Demo 1: Create CI/CD Pipeline
    print("\n1️⃣ Creating CI/CD Pipeline")
    print("-" * 32)

    pipeline_task = AgentTask(
        task_id="demo_pipeline_creation",
        type="create_pipeline",
        prompt="Create CI/CD pipeline for Python web application",
        context={
            "pipeline_type": "basic_python",
            "pipeline_config": {
                "variables": {
                    "DOCKER_REGISTRY": "registry.gitlab.com",
                    "APP_NAME": "agentic-workflow",
                },
                "deploy_production": {
                    "stage": "deploy",
                    "script": [
                        "kubectl apply -f k8s/production/",
                        "kubectl rollout status deployment/app",
                    ],
                    "only": ["main"],
                    "when": "manual",
                },
            },
        },
    )

    pipeline_result = await cicd_agent.execute(pipeline_task)

    if pipeline_result.success:
        print(f"✅ Pipeline created successfully")
        print(f"🎯 Pipeline type: {pipeline_result.data['pipeline_type']}")
        print(f"📋 Pipeline ID: {pipeline_result.data['pipeline_result']['pipeline_id']}")

        # Show a snippet of the generated GitLab CI YAML
        gitlab_ci = pipeline_result.data["gitlab_ci_content"]
        lines = gitlab_ci.split('\n')[:10]
        print(f"\n📝 Generated GitLab CI (first 10 lines):")
        for line in lines:
            print(f"   {line}")
        print("   ...")
    else:
        print("❌ Pipeline creation failed")

    # Demo 2: Deploy to Staging
    print("\n2️⃣ Deploying to Staging Environment")
    print("-" * 38)

    staging_deploy_task = AgentTask(
        task_id="demo_staging_deployment",
        type="deploy",
        prompt="Deploy application to staging environment",
        context={
            "environment": "staging",
            "branch": "develop",
            "config": {
                "replicas": 2,
                "build_args": {"ENV": "staging"},
                "env_vars": {
                    "DATABASE_URL": "postgres://staging-db:5432/app",
                    "REDIS_URL": "redis://staging-redis:6379",
                },
            },
        },
    )

    staging_result = await cicd_agent.execute(staging_deploy_task)

    if staging_result.success:
        deployment = staging_result.data["deployment_result"]
        print(f"✅ Deployment successful!")
        print(f"🌐 Environment: {staging_result.data['environment']}")
        print(f"🆔 Deployment ID: {staging_result.data['deployment_id']}")
        print(f"📦 Version: {deployment['version']}")
        print(f"⏱️  Status: {deployment['status']}")

        # Show deployment logs
        print(f"\n📋 Deployment Logs:")
        for i, log in enumerate(deployment['logs'][:4], 1):
            print(f"   {i}. {log}")

        # Show validation results
        validation = staging_result.data["validation_result"]
        print(f"\n🔍 Validation Results:")
        print(f"   ✅ Application Response: {validation['health_checks']['application_response']}")
        print(f"   ✅ Database Connection: {validation['health_checks']['database_connection']}")
        print(f"   📊 Response Time: {validation['performance_metrics']['response_time']}ms")
    else:
        print("❌ Staging deployment failed")

    # Demo 3: Environment Management
    print("\n3️⃣ Managing Deployment Environments")
    print("-" * 37)

    # Create development environment
    env_create_task = AgentTask(
        task_id="demo_env_creation",
        type="manage_environment",
        prompt="Create development environment",
        context={
            "action": "create",
            "environment": "development",
            "config": {
                "replicas": 1,
                "resources": {
                    "cpu": "100m",
                    "memory": "256Mi",
                },
            },
        },
    )

    env_result = await cicd_agent.execute(env_create_task)

    if env_result.success:
        env_data = env_result.data["environment_result"]
        print(f"✅ Environment created: {env_data['environment']}")
        print(f"🌐 URL: {env_data['url']}")
        print(f"📅 Created: {env_data['creation_time']}")
    else:
        print("❌ Environment creation failed")

    # Check environment status
    env_status_task = AgentTask(
        task_id="demo_env_status",
        type="manage_environment",
        prompt="Check staging environment status",
        context={
            "action": "status",
            "environment": "staging",
        },
    )

    status_result = await cicd_agent.execute(env_status_task)

    if status_result.success:
        status_data = status_result.data["environment_result"]
        print(f"\n📊 Staging Environment Status:")
        print(f"   Status: {status_data['status']}")
        print(f"   Version: {status_data['version']}")
        print(f"   Replicas: {status_data['replicas']}")
        print(f"   Health: {status_data['health']}")
        print(f"   Last Deployment: {status_data['last_deployment']}")

    # Demo 4: Health Monitoring
    print("\n4️⃣ Comprehensive Health Monitoring")
    print("-" * 38)

    health_task = AgentTask(
        task_id="demo_health_check",
        type="health_check",
        prompt="Perform comprehensive health check",
        context={
            "environment": "staging",
            "check_type": "comprehensive",
        },
    )

    health_result = await cicd_agent.execute(health_task)

    if health_result.success:
        health_data = health_result.data["health_result"]
        print(f"🏥 Overall Health: {'✅ Healthy' if health_data['overall_health'] else '❌ Unhealthy'}")
        print(f"🌐 Environment: {health_result.data['environment']}")

        checks = health_data["checks"]
        print(f"\n🔍 Health Check Details:")
        print(f"   Application: {'✅' if checks['application_health'] else '❌'}")
        print(f"   Database: {'✅' if checks['database_connectivity'] else '❌'}")
        print(f"   External Services: {'✅' if checks['external_service_connectivity'] else '❌'}")
        print(f"   SSL Certificate: {'✅' if checks['ssl_certificate'] else '❌'}")
        print(f"   Security Scan: {'✅' if checks['security_scan'] else '❌'}")

        resources = checks["resource_utilization"]
        print(f"\n📊 Resource Utilization:")
        print(f"   CPU: {resources['cpu_usage']:.1f}%")
        print(f"   Memory: {resources['memory_usage']:.1f}%")
        print(f"   Disk: {resources['disk_usage']:.1f}%")

        response_times = checks["response_times"]
        print(f"\n⚡ Response Times:")
        print(f"   Average: {response_times['average']}ms")
        print(f"   95th percentile: {response_times['p95']}ms")
        print(f"   99th percentile: {response_times['p99']}ms")
    else:
        print("❌ Health check failed")

    # Demo 5: Pipeline Status Monitoring
    print("\n5️⃣ Pipeline Status Monitoring")
    print("-" * 32)

    pipeline_status_task = AgentTask(
        task_id="demo_pipeline_status",
        type="pipeline_status",
        prompt="Check latest pipeline status",
        context={
            "branch": "develop",
        },
    )

    status_result = await cicd_agent.execute(pipeline_status_task)

    if status_result.success:
        pipeline_status = status_result.data["pipeline_status"]
        print(f"📋 Pipeline Status: {pipeline_status['status']}")
        print(f"🌿 Branch: {status_result.data['branch']}")
        print(f"🆔 Pipeline ID: {pipeline_status['pipeline_id']}")
        print(f"📅 Started: {pipeline_status['started_at']}")

        if pipeline_status['status'] == 'success':
            print(f"⏱️  Duration: {pipeline_status.get('duration', 'N/A')} seconds")

        print(f"🔧 Jobs: {', '.join(pipeline_status['jobs'])}")
    else:
        print("❌ Pipeline status check failed")

    # Demo 6: Rollback Operation
    print("\n6️⃣ Rollback Operation")
    print("-" * 23)

    rollback_task = AgentTask(
        task_id="demo_rollback",
        type="rollback",
        prompt="Rollback staging to previous stable version",
        context={
            "environment": "staging",
            "target_version": "v1.0.20240603",
        },
    )

    rollback_result = await cicd_agent.execute(rollback_task)

    if rollback_result.success:
        rollback_data = rollback_result.data["rollback_result"]
        print(f"🔄 Rollback successful!")
        print(f"🌐 Environment: {rollback_result.data['environment']}")
        print(f"📦 Rolled back to: {rollback_data['rolled_back_to']}")
        print(f"📅 Rollback time: {rollback_data['rollback_time']}")

        print(f"\n📋 Rollback Logs:")
        for i, log in enumerate(rollback_data['rollback_logs'], 1):
            print(f"   {i}. {log}")
    else:
        print("❌ Rollback failed")

    # Demo 7: Planning Capabilities
    print("\n7️⃣ Deployment Planning Capabilities")
    print("-" * 39)

    objective = "Deploy new microservice to production with zero downtime"
    tasks = await cicd_agent.plan(objective)

    print(f"📋 Generated {len(tasks)} tasks for objective:")
    print(f"   '{objective}'")
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

    print(f"📊 Total estimated duration: {total_duration} hours")

    # Demo 8: Agent Capabilities
    print("\n8️⃣ CI/CD Agent Capabilities")
    print("-" * 31)

    capabilities = cicd_agent.get_capabilities()
    print("🛠️  Available capabilities:")
    for i, capability in enumerate(capabilities, 1):
        print(f"   {i:2d}. {capability.replace('_', ' ').title()}")

    print("\n" + "=" * 65)
    print("✨ CI/CD Agent demonstration completed!")
    print("   The agent can automate complete deployment lifecycles")
    print("   from pipeline creation to production rollbacks.")


async def demonstrate_production_deployment():
    """Demonstrate a production-like deployment scenario."""

    print("\n" + "=" * 65)
    print("🏭 Production Deployment Scenario")
    print("=" * 65)

    # Initialize CI/CD Agent for production scenario
    production_config = {
        "gitlab_url": "https://gitlab.company.com",
        "supported_environments": ["staging", "production"],
        "deployment_timeout": 1200,  # 20 minutes for production
        "auto_rollback_enabled": True,
        "rollback_timeout": 300,
    }

    cicd_agent = CICDAgent(config=production_config)
    await cicd_agent.initialize()

    print("\n🎯 Scenario: Deploy critical bug fix to production")
    print("-" * 52)

    # Step 1: Create production-ready pipeline
    prod_pipeline_task = AgentTask(
        task_id="prod_pipeline",
        type="create_pipeline",
        prompt="Create production deployment pipeline with approval gates",
        context={
            "pipeline_type": "kubernetes_deployment",
            "pipeline_config": {
                "variables": {
                    "ENVIRONMENT": "production",
                    "REPLICAS": "5",
                },
                "deploy_production": {
                    "stage": "deploy",
                    "when": "manual",
                    "only": ["main"],
                    "script": [
                        "kubectl set image deployment/app app=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA",
                        "kubectl rollout status deployment/app --timeout=600s",
                    ],
                },
            },
        },
    )

    pipeline_result = await cicd_agent.execute(prod_pipeline_task)

    if pipeline_result.success:
        print("✅ Production pipeline created with manual approval gates")
        print(f"🔒 Security: Manual approval required for production deployment")

    # Step 2: Deploy to production
    prod_deploy_task = AgentTask(
        task_id="prod_deployment",
        type="deploy",
        prompt="Deploy bug fix to production environment",
        context={
            "environment": "production",
            "branch": "main",
            "config": {
                "replicas": 5,
                "build_args": {"ENV": "production"},
                "env_vars": {
                    "DATABASE_URL": "postgres://prod-db-cluster:5432/app",
                    "REDIS_URL": "redis://prod-redis-cluster:6379",
                    "LOG_LEVEL": "INFO",
                },
            },
        },
    )

    deploy_result = await cicd_agent.execute(prod_deploy_task)

    if deploy_result.success:
        deployment = deploy_result.data["deployment_result"]
        print(f"\n🚀 Production deployment initiated!")
        print(f"📦 Version: {deployment['version']}")
        print(f"🔢 Replicas: {deployment['metrics']['replicas']}")
        print(f"⏱️  Deployment time: {deployment['metrics']['deployment_time']} seconds")

    # Step 3: Comprehensive production health check
    prod_health_task = AgentTask(
        task_id="prod_health",
        type="health_check",
        prompt="Perform critical production health validation",
        context={
            "environment": "production",
            "check_type": "comprehensive",
        },
    )

    health_result = await cicd_agent.execute(prod_health_task)

    if health_result.success:
        health_data = health_result.data["health_result"]
        if health_data["overall_health"]:
            print(f"\n✅ Production health validation PASSED")
            print(f"🎯 All systems operational")
        else:
            print(f"\n⚠️  Production health validation FAILED")
            print(f"🚨 Initiating automatic rollback...")

    print("\n💼 Production deployment scenario completed!")
    print("   Real-world deployment with safety checks and validation.")


if __name__ == "__main__":
    # Run the comprehensive demonstrations
    print("🚀 Starting CI/CD Agent Comprehensive Demo...")

    # Main demonstration
    asyncio.run(demonstrate_cicd_agent())

    # Production scenario
    asyncio.run(demonstrate_production_deployment())

    print("\n💡 Next steps:")
    print("   1. Configure GitLab CI/CD integration")
    print("   2. Set up Kubernetes cluster for deployments")
    print("   3. Configure monitoring and alerting")
    print("   4. Set up automated rollback policies")
