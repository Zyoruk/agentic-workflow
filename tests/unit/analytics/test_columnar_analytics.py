"""
Tests for columnar analytics service using DuckDB and Parquet.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from agentic_workflow.analytics.columnar_analytics import (
    AnalyticsService,
    WorkflowMetric,
    UsageMetric,
    TenantAnalytics,
)
from agentic_workflow.core.tenant import TierType


@pytest.fixture
def temp_analytics_dir():
    """Create temporary directory for analytics data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def analytics_service(temp_analytics_dir):
    """Create analytics service with temporary storage."""
    service = AnalyticsService(data_dir=temp_analytics_dir)
    yield service
    service.close()


@pytest.mark.asyncio
async def test_initialize_analytics_service(analytics_service):
    """Test analytics service initialization."""
    assert analytics_service.workflow_metrics_path.exists()
    assert analytics_service.usage_metrics_path.exists()
    assert analytics_service.db_path.exists()


@pytest.mark.asyncio
async def test_record_workflow_metric(analytics_service):
    """Test recording a workflow metric."""
    started = datetime.now(timezone.utc)
    completed = started + timedelta(seconds=5)
    
    metric = WorkflowMetric(
        tenant_id="tenant_123",
        execution_id="exec_001",
        workflow_type="code_generation",
        agent_type="planning",
        tier=TierType.BUSINESS,
        started_at=started,
        completed_at=completed,
        duration_ms=5000.0,
        tokens_used=1500,
        files_processed=2,
        storage_mb=10.5,
        status="completed",
        estimated_cost=0.05,
    )
    
    await analytics_service.record_workflow_metric(metric)
    
    # Verify metric was recorded
    assert analytics_service.workflow_metrics_path.exists()


@pytest.mark.asyncio
async def test_record_usage_metric(analytics_service):
    """Test recording a usage metric."""
    metric = UsageMetric(
        tenant_id="tenant_123",
        date=datetime.now(timezone.utc),
        tier=TierType.STANDARD,
        total_requests=100,
        total_tokens=50000,
        total_files=10,
        total_storage_mb=50.0,
        successful_requests=95,
        failed_requests=5,
        average_duration_ms=2500.0,
        daily_cost=5.99,
    )
    
    await analytics_service.record_usage_metric(metric)
    
    # Verify metric was recorded
    assert analytics_service.usage_metrics_path.exists()


@pytest.mark.asyncio
async def test_get_tenant_analytics_empty(analytics_service):
    """Test getting analytics with no data."""
    analytics = await analytics_service.get_tenant_analytics(
        tenant_id="tenant_nonexistent",
        days=30
    )
    
    assert analytics.total_executions == 0
    assert analytics.success_rate == 0.0
    assert analytics.total_cost == 0.0


@pytest.mark.asyncio
async def test_get_tenant_analytics_with_data(analytics_service):
    """Test getting analytics with recorded data."""
    tenant_id = "tenant_analytics_test"
    
    # Record some workflow metrics
    for i in range(5):
        started = datetime.now(timezone.utc) - timedelta(days=i)
        completed = started + timedelta(seconds=3)
        
        metric = WorkflowMetric(
            tenant_id=tenant_id,
            execution_id=f"exec_{i}",
            workflow_type="analysis",
            agent_type="planning",
            tier=TierType.BUSINESS,
            started_at=started,
            completed_at=completed,
            duration_ms=3000.0,
            tokens_used=1000,
            files_processed=1,
            storage_mb=5.0,
            status="completed" if i < 4 else "failed",
            error_message="Test error" if i == 4 else None,
            estimated_cost=0.03,
        )
        
        await analytics_service.record_workflow_metric(metric)
    
    # Get analytics
    analytics = await analytics_service.get_tenant_analytics(
        tenant_id=tenant_id,
        days=30
    )
    
    assert analytics.total_executions == 5
    assert analytics.successful_executions == 4
    assert analytics.failed_executions == 1
    assert analytics.success_rate == 0.8
    assert analytics.total_tokens == 5000
    assert analytics.total_cost == 0.15
    assert len(analytics.daily_execution_trend) > 0


@pytest.mark.asyncio
async def test_get_cross_tenant_analytics(analytics_service):
    """Test getting cross-tenant analytics."""
    # Record metrics for multiple tenants
    for tenant_num in range(3):
        for i in range(2):
            started = datetime.now(timezone.utc) - timedelta(hours=i)
            completed = started + timedelta(seconds=2)
            
            metric = WorkflowMetric(
                tenant_id=f"tenant_{tenant_num}",
                execution_id=f"exec_{tenant_num}_{i}",
                workflow_type="test",
                agent_type="planning",
                tier=TierType.STANDARD if tenant_num % 2 == 0 else TierType.BUSINESS,
                started_at=started,
                completed_at=completed,
                duration_ms=2000.0,
                tokens_used=500,
                files_processed=0,
                storage_mb=0.0,
                status="completed",
                estimated_cost=0.02,
            )
            
            await analytics_service.record_workflow_metric(metric)
    
    # Get cross-tenant analytics
    analytics = await analytics_service.get_cross_tenant_analytics(days=1)
    
    assert analytics["total_executions"] == 6
    assert analytics["total_tokens"] == 3000
    assert "tier_distribution" in analytics


@pytest.mark.asyncio
async def test_performance_percentiles(analytics_service):
    """Test performance percentile calculations."""
    tenant_id = "tenant_perf_test"
    
    # Record metrics with varying durations
    durations = [1000, 2000, 3000, 5000, 10000]  # ms
    for i, duration in enumerate(durations):
        started = datetime.now(timezone.utc)
        completed = started + timedelta(milliseconds=duration)
        
        metric = WorkflowMetric(
            tenant_id=tenant_id,
            execution_id=f"exec_{i}",
            workflow_type="test",
            agent_type="planning",
            tier=TierType.BUSINESS,
            started_at=started,
            completed_at=completed,
            duration_ms=float(duration),
            tokens_used=100,
            files_processed=0,
            storage_mb=0.0,
            status="completed",
            estimated_cost=0.01,
        )
        
        await analytics_service.record_workflow_metric(metric)
    
    # Get analytics with percentiles
    analytics = await analytics_service.get_tenant_analytics(
        tenant_id=tenant_id,
        days=1
    )
    
    assert analytics.p50_duration_ms > 0
    assert analytics.p95_duration_ms > analytics.p50_duration_ms
    assert analytics.p99_duration_ms >= analytics.p95_duration_ms
