"""
Sentiment analysis for workflow prompts and results.

This module provides sentiment analysis capabilities for Business tier
customers to gain insights into user satisfaction and content tone.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from textblob import TextBlob

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SentimentPolarity(str, Enum):
    """Sentiment polarity classification."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentResult(BaseModel):
    """Sentiment analysis result."""

    analysis_id: str = Field(default_factory=lambda: f"sent_{uuid4().hex[:12]}")
    text: str
    polarity: float = Field(
        description="Sentiment polarity score (-1 to 1, negative to positive)"
    )
    subjectivity: float = Field(
        description="Subjectivity score (0 to 1, objective to subjective)"
    )
    classification: SentimentPolarity
    word_count: int
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Detailed metrics
    positive_words: List[str] = []
    negative_words: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SentimentBatch(BaseModel):
    """Batch sentiment analysis results."""

    batch_id: str = Field(default_factory=lambda: f"batch_{uuid4().hex[:12]}")
    tenant_id: str
    results: List[SentimentResult]
    
    # Aggregate metrics
    average_polarity: float
    average_subjectivity: float
    positive_count: int
    neutral_count: int
    negative_count: int
    
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SentimentTrend(BaseModel):
    """Sentiment trend over time."""

    tenant_id: str
    date_range_days: int
    
    # Trend data
    daily_polarity: List[Dict[str, float]]  # [{date, polarity}, ...]
    overall_sentiment: SentimentPolarity
    sentiment_distribution: Dict[SentimentPolarity, int]
    
    # Insights
    most_positive_day: Optional[str] = None
    most_negative_day: Optional[str] = None
    sentiment_volatility: float = 0.0  # Standard deviation of daily sentiment


class SentimentAnalyzer:
    """
    Sentiment analysis service for Business tier customers.
    
    Provides insights into prompt sentiment, user satisfaction trends,
    and content tone analysis using TextBlob NLP library.
    """

    def __init__(self):
        """Initialize sentiment analyzer."""
        self._positive_words = {
            "excellent", "great", "good", "awesome", "amazing", "fantastic",
            "wonderful", "perfect", "love", "like", "helpful", "best",
            "outstanding", "superior", "brilliant", "exceptional"
        }
        self._negative_words = {
            "bad", "poor", "terrible", "awful", "horrible", "hate", "worst",
            "disappointing", "useless", "broken", "failed", "error",
            "difficult", "frustrating", "confusing", "slow"
        }
        logger.info("SentimentAnalyzer initialized")

    async def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            SentimentResult with polarity, subjectivity, and classification
        """
        try:
            # Use TextBlob for sentiment analysis
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Classify sentiment
            if polarity > 0.1:
                classification = SentimentPolarity.POSITIVE
            elif polarity < -0.1:
                classification = SentimentPolarity.NEGATIVE
            else:
                classification = SentimentPolarity.NEUTRAL
            
            # Extract positive/negative words
            words = text.lower().split()
            positive_words = [w for w in words if w in self._positive_words]
            negative_words = [w for w in words if w in self._negative_words]
            
            result = SentimentResult(
                text=text[:500],  # Store first 500 chars
                polarity=polarity,
                subjectivity=subjectivity,
                classification=classification,
                word_count=len(words),
                positive_words=positive_words[:10],  # Top 10
                negative_words=negative_words[:10],  # Top 10
            )
            
            logger.info(
                f"Analyzed sentiment: {classification.value} "
                f"(polarity={polarity:.2f}, subjectivity={subjectivity:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            raise

    async def analyze_batch(
        self,
        tenant_id: str,
        texts: List[str]
    ) -> SentimentBatch:
        """
        Analyze sentiment for multiple texts in batch.
        
        Args:
            tenant_id: Tenant ID for tracking
            texts: List of texts to analyze
            
        Returns:
            SentimentBatch with aggregated results
        """
        try:
            results = []
            for text in texts:
                result = await self.analyze_text(text)
                results.append(result)
            
            # Calculate aggregates
            avg_polarity = sum(r.polarity for r in results) / len(results) if results else 0.0
            avg_subjectivity = sum(r.subjectivity for r in results) / len(results) if results else 0.0
            
            positive_count = sum(1 for r in results if r.classification == SentimentPolarity.POSITIVE)
            neutral_count = sum(1 for r in results if r.classification == SentimentPolarity.NEUTRAL)
            negative_count = sum(1 for r in results if r.classification == SentimentPolarity.NEGATIVE)
            
            batch = SentimentBatch(
                tenant_id=tenant_id,
                results=results,
                average_polarity=avg_polarity,
                average_subjectivity=avg_subjectivity,
                positive_count=positive_count,
                neutral_count=neutral_count,
                negative_count=negative_count,
            )
            
            logger.info(
                f"Batch analysis complete for tenant {tenant_id}: "
                f"{len(results)} texts, avg polarity={avg_polarity:.2f}"
            )
            
            return batch
            
        except Exception as e:
            logger.error(f"Error in batch sentiment analysis: {e}")
            raise

    async def get_sentiment_insights(
        self,
        results: List[SentimentResult]
    ) -> Dict[str, any]:
        """
        Generate insights from sentiment results.
        
        Args:
            results: List of sentiment results
            
        Returns:
            Dict with insights and recommendations
        """
        if not results:
            return {
                "insights": [],
                "recommendations": [],
                "summary": "No data available for analysis"
            }
        
        insights = []
        recommendations = []
        
        # Calculate metrics
        avg_polarity = sum(r.polarity for r in results) / len(results)
        positive_pct = (sum(1 for r in results if r.classification == SentimentPolarity.POSITIVE) / len(results)) * 100
        negative_pct = (sum(1 for r in results if r.classification == SentimentPolarity.NEGATIVE) / len(results)) * 100
        
        # Generate insights
        if avg_polarity > 0.3:
            insights.append("Overall sentiment is highly positive")
        elif avg_polarity < -0.3:
            insights.append("Overall sentiment is concerning - needs attention")
        else:
            insights.append("Sentiment is neutral - stable state")
        
        if positive_pct > 70:
            insights.append(f"Strong positive sentiment: {positive_pct:.1f}% of interactions")
        elif negative_pct > 30:
            insights.append(f"High negative sentiment: {negative_pct:.1f}% of interactions")
        
        # Generate recommendations
        if negative_pct > 30:
            recommendations.append("Review negative interactions for common issues")
            recommendations.append("Consider improving error messages or user guidance")
        
        if positive_pct > 70:
            recommendations.append("Leverage positive feedback in marketing materials")
            recommendations.append("Maintain current service quality standards")
        
        # Identify common words
        all_positive = []
        all_negative = []
        for r in results:
            all_positive.extend(r.positive_words)
            all_negative.extend(r.negative_words)
        
        # Count frequency
        from collections import Counter
        positive_freq = Counter(all_positive).most_common(5)
        negative_freq = Counter(all_negative).most_common(5)
        
        return {
            "insights": insights,
            "recommendations": recommendations,
            "summary": f"Analyzed {len(results)} texts with {avg_polarity:.2f} average polarity",
            "common_positive_words": [word for word, count in positive_freq],
            "common_negative_words": [word for word, count in negative_freq],
            "sentiment_distribution": {
                "positive": f"{positive_pct:.1f}%",
                "neutral": f"{100 - positive_pct - negative_pct:.1f}%",
                "negative": f"{negative_pct:.1f}%"
            }
        }


# Singleton instance
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create the singleton sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
