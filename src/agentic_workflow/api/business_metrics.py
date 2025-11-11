"""
Business tier metrics and analytics API endpoints.

Provides advanced analytics, sentiment analysis, and performance metrics
exclusively for Business tier customers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..analytics import (
    AnalyticsService,
    SentimentAnalyzer,
    WorkflowMetric,
    get_analytics_service,
    get_sentiment_analyzer,
)
from ..api.tier_auth import require_tier
from ..core.tenant import Tenant, TierType
from ..core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/business-metrics", tags=["Business Metrics"])


class AnalyticsRequest(BaseModel):
    """Request for tenant analytics."""

    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to analyze"
    )


class SentimentAnalysisRequest(BaseModel):
    """Request for sentiment analysis."""

    texts: List[str] = Field(
        description="Texts to analyze (prompts, results, feedback)"
    )


class WorkflowMetricRequest(BaseModel):
    """Request to record a workflow metric."""

    execution_id: str
    workflow_type: str
    agent_type: str
    started_at: datetime
    completed_at: datetime
    tokens_used: int
    files_processed: int = 0
    storage_mb: float = 0.0
    status: str = "completed"
    error_message: Optional[str] = None
    estimated_cost: float = 0.0


@router.get("/analytics")
async def get_analytics(
    days: int = Query(default=30, ge=1, le=365),
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get comprehensive analytics for the tenant (Business tier only).
    
    Returns workflow metrics, usage patterns, performance percentiles,
    and cost analysis using high-performance columnar processing.
    
    **Requires:** Business tier subscription
    """
    try:
        analytics = await analytics_service.get_tenant_analytics(
            tenant_id=tenant.id,
            days=days
        )
        
        logger.info(f"Retrieved analytics for tenant {tenant.id} ({days} days)")
        
        return {
            "status": "success",
            "tenant_id": tenant.id,
            "tier": tenant.tier.value,
            "analytics": analytics.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.get("/cross-tenant-analytics")
async def get_cross_tenant_analytics(
    days: int = Query(default=30, ge=1, le=365),
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get cross-tenant analytics (Business tier admin only).
    
    Provides insights across all tenants for platform-wide metrics,
    tier distribution, and revenue analysis.
    
    **Requires:** Business tier subscription
    """
    try:
        analytics = await analytics_service.get_cross_tenant_analytics(days=days)
        
        logger.info(f"Retrieved cross-tenant analytics for tenant {tenant.id}")
        
        return {
            "status": "success",
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error retrieving cross-tenant analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cross-tenant analytics: {str(e)}"
        )


@router.post("/record-metric")
async def record_workflow_metric(
    request: WorkflowMetricRequest,
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Record a workflow execution metric (Business tier only).
    
    Metrics are stored in Parquet format for high-performance
    columnar analytics with DuckDB.
    
    **Requires:** Business tier subscription
    """
    try:
        duration_ms = (request.completed_at - request.started_at).total_seconds() * 1000
        
        metric = WorkflowMetric(
            tenant_id=tenant.id,
            execution_id=request.execution_id,
            workflow_type=request.workflow_type,
            agent_type=request.agent_type,
            tier=tenant.tier,
            started_at=request.started_at,
            completed_at=request.completed_at,
            duration_ms=duration_ms,
            tokens_used=request.tokens_used,
            files_processed=request.files_processed,
            storage_mb=request.storage_mb,
            status=request.status,
            error_message=request.error_message,
            estimated_cost=request.estimated_cost,
        )
        
        await analytics_service.record_workflow_metric(metric)
        
        logger.info(f"Recorded workflow metric: {metric.metric_id}")
        
        return {
            "status": "success",
            "metric_id": metric.metric_id,
            "message": "Workflow metric recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error recording workflow metric: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record workflow metric: {str(e)}"
        )


@router.post("/sentiment-analysis")
async def analyze_sentiment(
    request: SentimentAnalysisRequest,
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    sentiment_analyzer: SentimentAnalyzer = Depends(get_sentiment_analyzer)
):
    """
    Analyze sentiment of texts (Business tier only).
    
    Provides sentiment polarity, subjectivity analysis, and
    classification (positive/neutral/negative) for prompts,
    results, or any text content.
    
    **Requires:** Business tier subscription
    """
    try:
        if not request.texts:
            raise HTTPException(
                status_code=400,
                detail="No texts provided for analysis"
            )
        
        if len(request.texts) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 texts per request"
            )
        
        batch = await sentiment_analyzer.analyze_batch(
            tenant_id=tenant.id,
            texts=request.texts
        )
        
        # Get insights
        insights = await sentiment_analyzer.get_sentiment_insights(batch.results)
        
        logger.info(f"Sentiment analysis completed for tenant {tenant.id}: {len(request.texts)} texts")
        
        return {
            "status": "success",
            "batch_id": batch.batch_id,
            "tenant_id": tenant.id,
            "summary": {
                "total_analyzed": len(batch.results),
                "average_polarity": batch.average_polarity,
                "average_subjectivity": batch.average_subjectivity,
                "positive_count": batch.positive_count,
                "neutral_count": batch.neutral_count,
                "negative_count": batch.negative_count,
            },
            "results": [r.model_dump() for r in batch.results],
            "insights": insights
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze sentiment: {str(e)}"
        )


@router.get("/performance-report")
async def get_performance_report(
    days: int = Query(default=30, ge=1, le=365),
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get comprehensive performance report (Business tier only).
    
    Includes success rates, performance percentiles, cost analysis,
    and operational insights.
    
    **Requires:** Business tier subscription
    """
    try:
        analytics = await analytics_service.get_tenant_analytics(
            tenant_id=tenant.id,
            days=days
        )
        
        # Calculate additional metrics
        uptime_pct = (analytics.success_rate * 100) if analytics.total_executions > 0 else 0.0
        avg_cost = analytics.cost_per_execution
        
        # Performance rating
        if analytics.success_rate >= 0.99:
            performance_rating = "Excellent"
        elif analytics.success_rate >= 0.95:
            performance_rating = "Good"
        elif analytics.success_rate >= 0.90:
            performance_rating = "Fair"
        else:
            performance_rating = "Needs Improvement"
        
        report = {
            "status": "success",
            "tenant_id": tenant.id,
            "tier": tenant.tier.value,
            "report_period": f"Last {days} days",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            
            "executive_summary": {
                "total_executions": analytics.total_executions,
                "success_rate": f"{analytics.success_rate * 100:.2f}%",
                "performance_rating": performance_rating,
                "total_cost": f"${analytics.total_cost:.2f}",
                "average_cost_per_execution": f"${avg_cost:.4f}",
            },
            
            "performance_metrics": {
                "p50_latency_ms": analytics.p50_duration_ms,
                "p95_latency_ms": analytics.p95_duration_ms,
                "p99_latency_ms": analytics.p99_duration_ms,
                "average_duration_ms": analytics.average_duration_ms,
            },
            
            "resource_utilization": {
                "total_tokens": analytics.total_tokens,
                "total_files": analytics.total_files,
                "total_storage_mb": analytics.total_storage_mb,
            },
            
            "operational_insights": {
                "agent_distribution": analytics.agent_usage_distribution,
                "error_distribution": analytics.error_distribution,
                "daily_trend": analytics.daily_execution_trend,
            },
            
            "recommendations": _generate_recommendations(analytics)
        }
        
        logger.info(f"Generated performance report for tenant {tenant.id}")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate performance report: {str(e)}"
        )


def _generate_recommendations(analytics) -> List[str]:
    """Generate actionable recommendations based on analytics."""
    recommendations = []
    
    # Success rate recommendations
    if analytics.success_rate < 0.95:
        recommendations.append(
            "Consider investigating error patterns to improve success rate"
        )
    
    # Performance recommendations
    if analytics.p95_duration_ms > 10000:
        recommendations.append(
            "P95 latency exceeds 10 seconds - consider optimizing workflows"
        )
    
    # Cost recommendations
    if analytics.cost_per_execution > 0.5:
        recommendations.append(
            "Average cost per execution is high - review resource usage"
        )
    
    # Usage recommendations
    if analytics.total_executions < 10:
        recommendations.append(
            "Low usage detected - consider promoting features to users"
        )
    
    # Error handling
    if len(analytics.error_distribution) > 5:
        recommendations.append(
            "Multiple error types detected - prioritize error handling improvements"
        )
    
    if not recommendations:
        recommendations.append("System is performing optimally - maintain current practices")
    
    return recommendations


@router.get("/export-data")
async def export_analytics_data(
    days: int = Query(default=30, ge=1, le=365),
    format: str = Query(default="json", regex="^(json|csv)$"),
    tenant: Tenant = Depends(require_tier(TierType.BUSINESS)),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Export analytics data in JSON or CSV format (Business tier only).
    
    Allows downloading raw analytics data for external processing
    or integration with BI tools.
    
    **Requires:** Business tier subscription
    """
    try:
        analytics = await analytics_service.get_tenant_analytics(
            tenant_id=tenant.id,
            days=days
        )
        
        if format == "json":
            return {
                "status": "success",
                "format": "json",
                "data": analytics.model_dump()
            }
        else:
            # Return CSV format (simplified)
            csv_data = f"metric,value\n"
            csv_data += f"total_executions,{analytics.total_executions}\n"
            csv_data += f"success_rate,{analytics.success_rate}\n"
            csv_data += f"total_tokens,{analytics.total_tokens}\n"
            csv_data += f"average_duration_ms,{analytics.average_duration_ms}\n"
            csv_data += f"total_cost,{analytics.total_cost}\n"
            
            return {
                "status": "success",
                "format": "csv",
                "data": csv_data
            }
        
    except Exception as e:
        logger.error(f"Error exporting analytics data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export analytics data: {str(e)}"
        )
