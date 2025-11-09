"""
Demonstration of Tenant Management and File Attachment Features.

This example shows how to use the new tenant management and file attachment
capabilities including:
- Creating tenants with different tiers
- Managing tenant preferences
- Uploading and searching files
- Tracking usage and enforcing quotas
"""

import asyncio
from pathlib import Path

from agentic_workflow.core.tenant import TenantService, TierType
from agentic_workflow.core.file_attachment import FileService


async def main():
    """Run the demonstration."""
    print("=" * 70)
    print("Tenant Management and File Attachment System Demo")
    print("=" * 70)
    print()

    # Initialize services
    tenant_service = TenantService()
    file_service = FileService(tenant_service=tenant_service)

    # ========================================================================
    # Part 1: Tenant Management
    # ========================================================================
    print("Part 1: Tenant Management")
    print("-" * 70)

    # Create tenants with different tiers
    print("\n1. Creating tenants with different tiers...")
    
    free_tenant = await tenant_service.create_tenant(
        name="Startup Co (Free)",
        tier=TierType.FREE,
        metadata={"industry": "technology", "size": "small"},
    )
    print(f"✓ Created FREE tier tenant: {free_tenant.name}")
    print(f"  - Max prompt size: {free_tenant.get_limits().max_prompt_size} tokens")
    print(f"  - Requests/day: {free_tenant.get_limits().requests_per_day}")
    print(f"  - File attachments: {free_tenant.get_limits().file_attachments}")

    standard_tenant = await tenant_service.create_tenant(
        name="Growing Corp (Standard)",
        tier=TierType.STANDARD,
        metadata={"industry": "finance", "size": "medium"},
    )
    print(f"\n✓ Created STANDARD tier tenant: {standard_tenant.name}")
    print(f"  - Max prompt size: {standard_tenant.get_limits().max_prompt_size} tokens")
    print(f"  - Requests/day: {standard_tenant.get_limits().requests_per_day}")
    print(f"  - File attachments: {standard_tenant.get_limits().file_attachments}")
    print(f"  - Max file size: {standard_tenant.get_limits().max_file_size_mb}MB")

    business_tenant = await tenant_service.create_tenant(
        name="Enterprise Inc (Business)",
        tier=TierType.BUSINESS,
        metadata={"industry": "healthcare", "size": "large"},
    )
    print(f"\n✓ Created BUSINESS tier tenant: {business_tenant.name}")
    print(f"  - Max prompt size: {business_tenant.get_limits().max_prompt_size} tokens")
    print(f"  - Requests/day: {business_tenant.get_limits().requests_per_day}")
    print(f"  - File attachments: {business_tenant.get_limits().file_attachments}")
    print(f"  - Max file size: {business_tenant.get_limits().max_file_size_mb}MB")
    print(f"  - Audit logging: {business_tenant.get_limits().audit_logging}")

    # ========================================================================
    # Part 2: Preference Management
    # ========================================================================
    print("\n\nPart 2: Preference Management")
    print("-" * 70)

    # Try to set preferences for free tier (should fail)
    print("\n1. Attempting to set preferences for FREE tier...")
    try:
        await tenant_service.set_preference(
            free_tenant.id,
            "default_model",
            {"model": "gpt-4"},
        )
        print("✗ Should have failed!")
    except ValueError as e:
        print(f"✓ Expected error: {e}")

    # Set preferences for standard tier
    print("\n2. Setting preferences for STANDARD tier...")
    await tenant_service.set_preference(
        standard_tenant.id,
        "default_model",
        {"model": "gpt-4", "temperature": 0.7},
    )
    await tenant_service.set_preference(
        standard_tenant.id,
        "code_style",
        {"language": "python", "style": "black"},
    )
    print("✓ Set preferences for standard tenant")

    # Retrieve preferences
    preferences = await tenant_service.get_all_preferences(standard_tenant.id)
    print(f"\n✓ Retrieved {len(preferences)} preferences:")
    for key, pref in preferences.items():
        print(f"  - {key}: {pref.preference_value}")

    # ========================================================================
    # Part 3: File Upload and Management
    # ========================================================================
    print("\n\nPart 3: File Upload and Management")
    print("-" * 70)

    # Try to upload file with free tier (should fail)
    print("\n1. Attempting file upload with FREE tier...")
    try:
        await file_service.upload_file(
            tenant_id=free_tenant.id,
            filename="test.txt",
            content=b"This should fail",
            content_type="text/plain",
        )
        print("✗ Should have failed!")
    except ValueError as e:
        print(f"✓ Expected error: {e}")

    # Upload files with standard tier
    print("\n2. Uploading files with STANDARD tier...")
    
    doc1_content = b"""
    Python Programming Best Practices
    
    1. Use meaningful variable names
    2. Follow PEP 8 style guide
    3. Write comprehensive docstrings
    4. Use type hints for clarity
    5. Keep functions small and focused
    
    Example:
    def calculate_total(items: list[float]) -> float:
        '''Calculate the total sum of items.'''
        return sum(items)
    """

    doc1 = await file_service.upload_file(
        tenant_id=standard_tenant.id,
        filename="python_best_practices.txt",
        content=doc1_content,
        content_type="text/plain",
        metadata={
            "tags": ["python", "best-practices", "coding"],
            "description": "Python programming guidelines",
        },
    )
    print(f"✓ Uploaded: {doc1.filename}")
    print(f"  - Size: {doc1.size_bytes} bytes")
    print(f"  - Chunks: {doc1.chunks_count}")
    print(f"  - Hash: {doc1.content_hash[:16]}...")

    doc2_content = b"""
    JavaScript Development Guide
    
    1. Use const and let instead of var
    2. Embrace async/await for promises
    3. Use ESLint for code quality
    4. Implement proper error handling
    5. Write unit tests with Jest
    
    Example:
    async function fetchData(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Fetch failed:', error);
        }
    }
    """

    doc2 = await file_service.upload_file(
        tenant_id=standard_tenant.id,
        filename="javascript_guide.txt",
        content=doc2_content,
        content_type="text/plain",
        metadata={
            "tags": ["javascript", "development", "coding"],
            "description": "JavaScript development guidelines",
        },
    )
    print(f"\n✓ Uploaded: {doc2.filename}")
    print(f"  - Size: {doc2.size_bytes} bytes")
    print(f"  - Chunks: {doc2.chunks_count}")

    # List files
    print("\n3. Listing files for tenant...")
    files = await file_service.list_files(standard_tenant.id)
    print(f"✓ Found {len(files)} files:")
    for file in files:
        print(f"  - {file.filename} ({file.size_bytes} bytes)")

    # ========================================================================
    # Part 4: Semantic Search
    # ========================================================================
    print("\n\nPart 4: Semantic File Search")
    print("-" * 70)

    # Search for Python-related content
    print("\n1. Searching for 'Python'...")
    results = await file_service.search_files(
        tenant_id=standard_tenant.id,
        query="Python",
        limit=5,
    )
    print(f"✓ Found {len(results)} results:")
    for result in results:
        print(f"\n  File: {result.metadata['filename']}")
        print(f"  Score: {result.similarity_score:.2f}")
        print(f"  Content preview: {result.content[:100]}...")

    # Search for async/await
    print("\n2. Searching for 'async await'...")
    results = await file_service.search_files(
        tenant_id=standard_tenant.id,
        query="async await",
        limit=5,
    )
    print(f"✓ Found {len(results)} results:")
    for result in results:
        print(f"\n  File: {result.metadata['filename']}")
        print(f"  Score: {result.similarity_score:.2f}")
        print(f"  Content preview: {result.content[:100]}...")

    # ========================================================================
    # Part 5: Usage Tracking and Quotas
    # ========================================================================
    print("\n\nPart 5: Usage Tracking and Quota Management")
    print("-" * 70)

    # Track some usage
    print("\n1. Simulating API usage...")
    for i in range(5):
        await tenant_service.track_usage(
            standard_tenant.id,
            requests=1,
            tokens=1000,
        )
    print("✓ Tracked 5 requests (5000 tokens)")

    # Check usage
    print("\n2. Checking usage statistics...")
    usage = await tenant_service.get_usage(standard_tenant.id)
    if usage:
        quota_status = usage.get_quota_status(standard_tenant.get_limits())
        print(f"✓ Current usage:")
        print(f"  - Requests: {quota_status['requests']['used']}/{quota_status['requests']['limit']} "
              f"({quota_status['requests']['percentage']:.1f}%)")
        print(f"  - Tokens: {quota_status['tokens']['used']}")
        print(f"  - Files: {quota_status['files']['uploaded']}")
        print(f"  - Storage: {quota_status['storage']['used_mb']:.2f} MB")

    # Check quota
    print("\n3. Checking quota status...")
    quota_check = await tenant_service.check_quota(standard_tenant.id)
    print(f"✓ Quota check result: {'ALLOWED' if quota_check['allowed'] else 'DENIED'}")
    if not quota_check['allowed']:
        print(f"  Reason: {quota_check['reason']}")

    # Simulate exceeding quota
    print("\n4. Simulating quota exhaustion...")
    await tenant_service.track_usage(
        standard_tenant.id,
        requests=1000,  # Exhaust quota
    )
    quota_check = await tenant_service.check_quota(standard_tenant.id)
    print(f"✓ Quota check result: {'ALLOWED' if quota_check['allowed'] else 'DENIED'}")
    if not quota_check['allowed']:
        print(f"  Reason: {quota_check['reason']}")

    # ========================================================================
    # Part 6: Tier Upgrade
    # ========================================================================
    print("\n\nPart 6: Tier Management")
    print("-" * 70)

    print("\n1. Upgrading tenant from STANDARD to BUSINESS...")
    updated = await tenant_service.update_tenant(
        standard_tenant.id,
        tier=TierType.BUSINESS,
    )
    print(f"✓ Upgraded {updated.name} to {updated.tier}")
    print(f"  - New request limit: {updated.get_limits().requests_per_day}/day")
    print(f"  - New file size limit: {updated.get_limits().max_file_size_mb}MB")
    print(f"  - Audit logging: {updated.get_limits().audit_logging}")

    # ========================================================================
    # Part 7: Cleanup
    # ========================================================================
    print("\n\nPart 7: File Cleanup")
    print("-" * 70)

    print("\n1. Running expired file cleanup...")
    deleted = await file_service.cleanup_expired_files()
    print(f"✓ Cleaned up {deleted} expired files")

    # Delete a file manually
    print("\n2. Deleting a file manually...")
    await file_service.delete_file(doc1.id)
    print(f"✓ Deleted {doc1.filename}")

    # Verify deletion
    remaining_files = await file_service.list_files(standard_tenant.id)
    print(f"✓ Remaining files: {len(remaining_files)}")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nFeatures Demonstrated:")
    print("  ✓ Multi-tenant management with tier-based access")
    print("  ✓ Preference storage and retrieval")
    print("  ✓ File upload with intelligent chunking")
    print("  ✓ Semantic file search")
    print("  ✓ Usage tracking and quota enforcement")
    print("  ✓ Tier upgrade/downgrade")
    print("  ✓ File cleanup and management")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
