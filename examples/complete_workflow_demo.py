"""
Complete Workflow Demonstration - End-to-End User Experience.

This example demonstrates the seamless workflow where users can:
1. Send their prompt (any size)
2. Attach files to the prompt as context
3. Send preferences for the workflow to consider

The workflow automatically:
- Chunks large prompts
- Processes and stores files with vector embeddings
- Applies tenant preferences
- Enforces tier-based quotas
- Executes the appropriate agent workflow
"""

import asyncio
import json
from pathlib import Path

from agentic_workflow.core.tenant import TenantService, TierType
from agentic_workflow.core.file_attachment import FileService
from agentic_workflow.api.workflow_orchestration import (
    execute_workflow,
    get_workflow_status,
    list_executions,
)


async def main():
    """Run the complete workflow demonstration."""
    print("=" * 80)
    print("COMPLETE WORKFLOW ORCHESTRATION DEMO")
    print("Seamless End-to-End User Experience")
    print("=" * 80)
    print()

    # Initialize services
    tenant_service = TenantService()
    file_service = FileService(tenant_service=tenant_service)

    # ========================================================================
    # Setup: Create tenant and set preferences
    # ========================================================================
    print("Setup: Creating tenant and setting preferences")
    print("-" * 80)

    tenant = await tenant_service.create_tenant(
        name="Demo Company",
        tier=TierType.STANDARD,  # Full features
        metadata={"industry": "software", "size": "startup"},
    )
    print(f"✓ Created tenant: {tenant.name} (ID: {tenant.id[:8]}...)")
    print(f"  Tier: {tenant.tier}")
    print(f"  Max prompt size: {tenant.get_limits().max_prompt_size} tokens")
    print(f"  File attachments: {tenant.get_limits().file_attachments}")
    print()

    # Set some preferences
    await tenant_service.set_preference(
        tenant.id,
        "coding_style",
        {
            "language": "python",
            "style_guide": "PEP 8",
            "max_line_length": 88,
            "use_type_hints": True,
        },
    )
    await tenant_service.set_preference(
        tenant.id,
        "project_settings",
        {
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "testing": "pytest",
        },
    )
    print("✓ Set tenant preferences:")
    print("  - Coding style (Python, PEP 8)")
    print("  - Project settings (FastAPI, PostgreSQL, pytest)")
    print()

    # ========================================================================
    # Scenario 1: Simple prompt workflow (no files)
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 1: Simple Prompt Workflow")
    print("=" * 80)
    print()

    simple_prompt = """
    I need help designing a REST API for a task management system.
    The API should support:
    - Creating, reading, updating, and deleting tasks
    - Assigning tasks to users
    - Setting task priorities and due dates
    - Tracking task status (todo, in-progress, done)
    - Searching and filtering tasks
    
    Please create a comprehensive plan for implementing this API.
    """

    print("Prompt:")
    print(simple_prompt.strip())
    print()
    print("Executing workflow...")

    # Simulate the workflow orchestration call
    from unittest.mock import Mock
    from fastapi import UploadFile

    # Mock the Form data
    result = await execute_workflow(
        tenant_id=tenant.id,
        prompt=simple_prompt.strip(),
        files=None,
        preferences=None,
        agent_type="planning",
    )

    print(f"\n✓ Workflow completed: {result['execution_id']}")
    print(f"  Status: {result['status']}")
    print(f"  Prompt chunks: {result['prompt_info']['total_chunks']}")
    print(f"  Tokens used: {result['prompt_info']['estimated_tokens']}")
    print(f"  Preferences applied: {len(result['preferences_applied'])}")
    print()

    if result["agent_results"].get("success"):
        print("Agent Result:")
        print(f"  {str(result['agent_results']['result'])[:200]}...")
    print()

    # ========================================================================
    # Scenario 2: Workflow with file attachments
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 2: Workflow with File Attachments")
    print("=" * 80)
    print()

    # First, upload some files
    print("Uploading context files...")
    
    requirements_doc = b"""
    # Task Management System Requirements
    
    ## Functional Requirements
    
    1. User Management
       - Users can register and login
       - Users have roles: admin, manager, member
       
    2. Task Management
       - Create tasks with title, description, priority
       - Assign tasks to users
       - Set due dates
       - Update task status
       
    3. Search and Filtering
       - Search by title/description
       - Filter by status, priority, assignee
       - Sort by date, priority
    
    ## Non-Functional Requirements
    
    1. Performance
       - API response time < 200ms
       - Support 1000 concurrent users
       
    2. Security
       - JWT authentication
       - Role-based access control
       - Input validation
    """

    architecture_doc = b"""
    # Proposed Architecture
    
    ## Technology Stack
    
    - Backend: FastAPI (Python 3.11+)
    - Database: PostgreSQL 15
    - Cache: Redis
    - API Documentation: OpenAPI/Swagger
    
    ## API Structure
    
    ```
    /api/v1/
        /auth/
            POST /register
            POST /login
        /users/
            GET /users
            GET /users/{id}
        /tasks/
            POST /tasks
            GET /tasks
            GET /tasks/{id}
            PUT /tasks/{id}
            DELETE /tasks/{id}
    ```
    
    ## Database Schema
    
    - users (id, email, password_hash, role, created_at)
    - tasks (id, title, description, priority, status, assignee_id, due_date, created_at)
    """

    file1 = await file_service.upload_file(
        tenant_id=tenant.id,
        filename="requirements.txt",
        content=requirements_doc,
        content_type="text/plain",
    )
    print(f"✓ Uploaded: {file1.filename} ({file1.chunks_count} chunks)")

    file2 = await file_service.upload_file(
        tenant_id=tenant.id,
        filename="architecture.txt",
        content=architecture_doc,
        content_type="text/plain",
    )
    print(f"✓ Uploaded: {file2.filename} ({file2.chunks_count} chunks)")
    print()

    # Now execute workflow with files
    workflow_prompt = """
    Based on the requirements and architecture documents I've provided,
    please create a detailed implementation plan for the task management API.
    
    Include:
    1. Database migration scripts
    2. Pydantic models for request/response
    3. FastAPI route implementations
    4. Authentication middleware
    5. Unit test structure
    
    Follow the coding preferences I've set for Python and FastAPI.
    """

    print("Prompt:")
    print(workflow_prompt.strip())
    print()
    print(f"Attached files: {file1.filename}, {file2.filename}")
    print()
    print("Executing workflow with file context...")

    # Simulate workflow with files
    # In reality, we'd call the API with actual file uploads
    # For this demo, we'll create mock UploadFile objects
    
    # Instead, let's use the JSON API endpoint which is easier to demo
    from agentic_workflow.api.workflow_orchestration import WorkflowExecutionRequest
    
    json_request = WorkflowExecutionRequest(
        tenant_id=tenant.id,
        prompt=workflow_prompt.strip(),
        file_ids=[file1.id, file2.id],
        preferences={
            "output_format": "detailed",
            "include_tests": True,
        },
        agent_type="planning",
    )

    from agentic_workflow.api.workflow_orchestration import execute_workflow_json
    
    result2 = await execute_workflow_json(json_request)

    print(f"\n✓ Workflow completed: {result2['execution_id']}")
    print(f"  Status: {result2['status']}")
    print(f"  Prompt chunks: {result2['prompt_info']['total_chunks']}")
    print(f"  Files processed: {result2['files_processed']}")
    print(f"  Preferences applied: {len(result2['preferences_applied'])}")
    print()

    # Show preferences that were applied
    print("Applied preferences:")
    for key, value in result2["preferences_applied"].items():
        print(f"  - {key}: {json.dumps(value, indent=4)[:80]}...")
    print()

    # ========================================================================
    # Scenario 3: Large prompt with chunking
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 3: Large Prompt with Automatic Chunking")
    print("=" * 80)
    print()

    # Create a large prompt that will be chunked
    large_prompt = """
    I need help implementing a comprehensive microservices architecture.
    
    """ + "\n".join([
        f"Service {i}: This service handles {['authentication', 'user management', 'data processing', 'reporting', 'notifications'][i % 5]}. "
        f"It should include REST APIs, database persistence, caching, logging, monitoring, and error handling. "
        f"The service must be scalable, secure, and follow 2025 best practices. "
        * 10  # Repeat to make it longer
        for i in range(20)
    ])

    print(f"Prompt length: {len(large_prompt)} characters")
    print("First 200 characters:")
    print(large_prompt[:200] + "...")
    print()
    print("Executing workflow (will be automatically chunked)...")

    result3 = await execute_workflow(
        tenant_id=tenant.id,
        prompt=large_prompt,
        files=None,
        preferences='{"complexity": "high", "include_diagrams": false}',
        agent_type="planning",
    )

    print(f"\n✓ Workflow completed: {result3['execution_id']}")
    print(f"  Status: {result3['status']}")
    print(f"  Prompt was chunked into: {result3['prompt_info']['total_chunks']} pieces")
    print(f"  Total tokens: {result3['prompt_info']['estimated_tokens']}")
    print(f"  Chunk indices: {result3['prompt_info']['chunk_indices']}")
    print()

    # ========================================================================
    # Check usage and quotas
    # ========================================================================
    print("\n" + "=" * 80)
    print("USAGE TRACKING & QUOTA STATUS")
    print("=" * 80)
    print()

    usage = await tenant_service.get_usage(tenant.id)
    if usage:
        limits = tenant.get_limits()
        quota_status = usage.get_quota_status(limits)
        
        print(f"Tenant: {tenant.name}")
        print(f"Tier: {tenant.tier}")
        print()
        print("Current Usage:")
        print(f"  Requests: {quota_status['requests']['used']}/{quota_status['requests']['limit']} "
              f"({quota_status['requests']['percentage']:.1f}%)")
        print(f"  Tokens: {quota_status['tokens']['used']:,}")
        print(f"  Files: {quota_status['files']['uploaded']}")
        print(f"  Storage: {quota_status['storage']['used_mb']:.2f} MB")
        print()

    # ========================================================================
    # List all executions
    # ========================================================================
    print("\n" + "=" * 80)
    print("EXECUTION HISTORY")
    print("=" * 80)
    print()

    executions_list = await list_executions(tenant.id, limit=10)
    
    print(f"Total executions: {executions_list['total']}")
    print()
    print("Recent executions:")
    for i, exec_info in enumerate(executions_list["executions"], 1):
        print(f"{i}. {exec_info['execution_id']}")
        print(f"   Status: {exec_info['status']}")
        print(f"   Created: {exec_info['created_at']}")
        if exec_info.get('completed_at'):
            print(f"   Completed: {exec_info['completed_at']}")
        print()

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80)
    print()
    print("Features Demonstrated:")
    print("  ✓ Seamless workflow execution (prompt + files + preferences)")
    print("  ✓ Automatic prompt chunking for large inputs")
    print("  ✓ File attachment processing with vector storage")
    print("  ✓ Tenant preference application")
    print("  ✓ Tier-based quota enforcement")
    print("  ✓ Usage tracking and reporting")
    print("  ✓ Execution history tracking")
    print()
    print("The workflow orchestration API provides a complete end-to-end")
    print("experience that ties together all the infrastructure components!")
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
