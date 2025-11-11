"""
Phase 4: Business Tier Analytics and Sentiment Analysis Demo

This example demonstrates:
1. Columnar analytics with DuckDB and Parquet (10-100x performance)
2. Sentiment analysis for prompts and results
3. Performance metrics and insights
4. Business intelligence capabilities

Requirements:
- Business tier subscription
- DuckDB and PyArrow installed
- TextBlob for sentiment analysis
"""

import asyncio
from datetime import datetime, timedelta, timezone
import tempfile

from agentic_workflow.analytics import (
    AnalyticsService,
    SentimentAnalyzer,
    WorkflowMetric,
    UsageMetric,
)
from agentic_workflow.core.tenant import TierType


async def main():
    """Run Phase 4 analytics demo."""
    
    print("=" * 80)
    print("Phase 4: Business Tier Analytics & Sentiment Analysis Demo")
    print("=" * 80)
    print()
    
    # Initialize services
    with tempfile.TemporaryDirectory() as tmpdir:
        analytics_service = AnalyticsService(data_dir=tmpdir)
        sentiment_analyzer = SentimentAnalyzer()
        
        print("✅ Analytics service initialized with columnar storage (DuckDB + Parquet)")
        print()
        
        # =====================================================================
        # Part 1: Record Workflow Metrics
        # =====================================================================
        print("📊 Part 1: Recording Workflow Metrics")
        print("-" * 80)
        
        tenant_id = "business_tenant_001"
        
        # Simulate 30 days of workflow executions
        print(f"Simulating 30 days of workflow data for tenant: {tenant_id}")
        
        for day in range(30):
            date = datetime.now(timezone.utc) - timedelta(days=day)
            
            # Simulate 5-15 executions per day
            num_executions = 5 + (day % 10)
            
            for i in range(num_executions):
                started = date + timedelta(hours=i)
                duration_ms = 2000 + (i * 500)  # Varying durations
                completed = started + timedelta(milliseconds=duration_ms)
                
                # 95% success rate
                status = "completed" if i < num_executions * 0.95 else "failed"
                
                metric = WorkflowMetric(
                    tenant_id=tenant_id,
                    execution_id=f"exec_{day}_{i}",
                    workflow_type="code_generation" if i % 2 == 0 else "analysis",
                    agent_type="planning" if i % 3 == 0 else "cicd",
                    tier=TierType.BUSINESS,
                    started_at=started,
                    completed_at=completed,
                    duration_ms=duration_ms,
                    tokens_used=1000 + (i * 100),
                    files_processed=i % 3,
                    storage_mb=float(i * 2.5),
                    status=status,
                    error_message="Timeout error" if status == "failed" else None,
                    estimated_cost=0.05 * (1 + i * 0.01),
                )
                
                await analytics_service.record_workflow_metric(metric)
        
        print(f"✅ Recorded workflow metrics for 30 days")
        print()
        
        # =====================================================================
        # Part 2: Get Tenant Analytics
        # =====================================================================
        print("📈 Part 2: Retrieving Tenant Analytics")
        print("-" * 80)
        
        analytics = await analytics_service.get_tenant_analytics(
            tenant_id=tenant_id,
            days=30
        )
        
        print(f"Tenant ID: {analytics.tenant_id}")
        print(f"Tier: {analytics.tier.value}")
        print(f"Analysis Period: {analytics.date_range_days} days")
        print()
        
        print("📊 Execution Metrics:")
        print(f"  Total Executions: {analytics.total_executions}")
        print(f"  Successful: {analytics.successful_executions}")
        print(f"  Failed: {analytics.failed_executions}")
        print(f"  Success Rate: {analytics.success_rate * 100:.2f}%")
        print()
        
        print("⏱️  Performance Metrics:")
        print(f"  Average Duration: {analytics.average_duration_ms:.2f} ms")
        print(f"  P50 (Median): {analytics.p50_duration_ms:.2f} ms")
        print(f"  P95: {analytics.p95_duration_ms:.2f} ms")
        print(f"  P99: {analytics.p99_duration_ms:.2f} ms")
        print()
        
        print("💰 Cost Analysis:")
        print(f"  Total Cost: ${analytics.total_cost:.2f}")
        print(f"  Cost Per Execution: ${analytics.cost_per_execution:.4f}")
        print()
        
        print("📦 Resource Utilization:")
        print(f"  Total Tokens: {analytics.total_tokens:,}")
        print(f"  Total Files: {analytics.total_files}")
        print(f"  Total Storage: {analytics.total_storage_mb:.2f} MB")
        print()
        
        print("🎯 Agent Distribution:")
        for agent, count in analytics.agent_usage_distribution.items():
            print(f"  {agent}: {count} executions")
        print()
        
        if analytics.error_distribution:
            print("⚠️  Error Distribution:")
            for error, count in analytics.error_distribution.items():
                print(f"  {error}: {count} occurrences")
            print()
        
        # =====================================================================
        # Part 3: Cross-Tenant Analytics
        # =====================================================================
        print("🌐 Part 3: Cross-Tenant Analytics")
        print("-" * 80)
        
        # Record data for other tenants
        for tenant_num in range(3):
            for i in range(5):
                started = datetime.now(timezone.utc) - timedelta(hours=i)
                completed = started + timedelta(seconds=3)
                
                metric = WorkflowMetric(
                    tenant_id=f"tenant_{tenant_num}",
                    execution_id=f"exec_{tenant_num}_{i}",
                    workflow_type="test",
                    agent_type="planning",
                    tier=TierType.STANDARD if tenant_num % 2 == 0 else TierType.BUSINESS,
                    started_at=started,
                    completed_at=completed,
                    duration_ms=3000.0,
                    tokens_used=500,
                    files_processed=0,
                    storage_mb=0.0,
                    status="completed",
                    estimated_cost=0.02,
                )
                
                await analytics_service.record_workflow_metric(metric)
        
        cross_tenant = await analytics_service.get_cross_tenant_analytics(days=1)
        
        print("Platform-Wide Metrics (Last 24 Hours):")
        print(f"  Total Executions: {cross_tenant['total_executions']}")
        print(f"  Total Tokens: {cross_tenant['total_tokens']:,}")
        print(f"  Average Duration: {cross_tenant['average_duration_ms']:.2f} ms")
        print(f"  Total Revenue: ${cross_tenant['total_revenue']:.2f}")
        print()
        
        print("Tier Distribution:")
        for tier, count in cross_tenant['tier_distribution'].items():
            print(f"  {tier}: {count} tenants")
        print()
        
        # =====================================================================
        # Part 4: Sentiment Analysis
        # =====================================================================
        print("😊 Part 4: Sentiment Analysis")
        print("-" * 80)
        
        # Sample prompts and feedback
        prompts = [
            "Create an excellent REST API with amazing documentation",
            "Build a terrible authentication system with poor security",
            "Implement a standard user management module",
            "Design a fantastic database schema with great performance",
            "Fix the broken error handling in the application",
        ]
        
        print("Analyzing sentiment of prompts:")
        print()
        
        batch = await sentiment_analyzer.analyze_batch(
            tenant_id=tenant_id,
            texts=prompts
        )
        
        print(f"Batch Analysis Summary:")
        print(f"  Texts Analyzed: {len(batch.results)}")
        print(f"  Average Polarity: {batch.average_polarity:.3f}")
        print(f"  Average Subjectivity: {batch.average_subjectivity:.3f}")
        print(f"  Positive: {batch.positive_count}")
        print(f"  Neutral: {batch.neutral_count}")
        print(f"  Negative: {batch.negative_count}")
        print()
        
        print("Individual Results:")
        for i, result in enumerate(batch.results, 1):
            print(f"\n  {i}. Text: {result.text[:60]}...")
            print(f"     Classification: {result.classification.value}")
            print(f"     Polarity: {result.polarity:.3f}")
            print(f"     Subjectivity: {result.subjectivity:.3f}")
            if result.positive_words:
                print(f"     Positive Words: {', '.join(result.positive_words)}")
            if result.negative_words:
                print(f"     Negative Words: {', '.join(result.negative_words)}")
        print()
        
        # =====================================================================
        # Part 5: Sentiment Insights
        # =====================================================================
        print("💡 Part 5: Sentiment Insights & Recommendations")
        print("-" * 80)
        
        insights = await sentiment_analyzer.get_sentiment_insights(batch.results)
        
        print("Key Insights:")
        for insight in insights["insights"]:
            print(f"  • {insight}")
        print()
        
        print("Recommendations:")
        for rec in insights["recommendations"]:
            print(f"  • {rec}")
        print()
        
        print("Sentiment Distribution:")
        for sentiment, percentage in insights["sentiment_distribution"].items():
            print(f"  {sentiment}: {percentage}")
        print()
        
        if insights.get("common_positive_words"):
            print("Most Common Positive Words:")
            print(f"  {', '.join(insights['common_positive_words'])}")
            print()
        
        if insights.get("common_negative_words"):
            print("Most Common Negative Words:")
            print(f"  {', '.join(insights['common_negative_words'])}")
            print()
        
        # =====================================================================
        # Summary
        # =====================================================================
        print("=" * 80)
        print("✅ Phase 4 Demo Complete!")
        print("=" * 80)
        print()
        print("Key Achievements:")
        print("  ✅ Columnar analytics with DuckDB + Parquet (10-100x performance)")
        print("  ✅ Comprehensive workflow metrics and KPIs")
        print("  ✅ Performance percentiles (P50, P95, P99)")
        print("  ✅ Cross-tenant analytics for platform insights")
        print("  ✅ Sentiment analysis with polarity and subjectivity")
        print("  ✅ Automated insights and recommendations")
        print()
        print("Business Value:")
        print("  📈 High-performance analytics for large datasets")
        print("  🎯 Actionable insights from workflow data")
        print("  💰 Cost optimization opportunities identified")
        print("  😊 User satisfaction tracking via sentiment")
        print("  📊 Executive dashboards and reports ready")
        print()
        
        # Cleanup
        analytics_service.close()


if __name__ == "__main__":
    asyncio.run(main())
