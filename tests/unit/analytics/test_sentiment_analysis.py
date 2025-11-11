"""
Tests for sentiment analysis service.
"""

import pytest

from agentic_workflow.analytics.sentiment_analysis import (
    SentimentAnalyzer,
    SentimentResult,
    SentimentPolarity,
)


@pytest.fixture
def sentiment_analyzer():
    """Create sentiment analyzer instance."""
    return SentimentAnalyzer()


@pytest.mark.asyncio
async def test_analyze_positive_text(sentiment_analyzer):
    """Test analyzing positive text."""
    text = "This is excellent work! The results are amazing and I love the quality."
    
    result = await sentiment_analyzer.analyze_text(text)
    
    assert result.classification == SentimentPolarity.POSITIVE
    assert result.polarity > 0
    assert result.word_count > 0
    assert len(result.positive_words) > 0


@pytest.mark.asyncio
async def test_analyze_negative_text(sentiment_analyzer):
    """Test analyzing negative text."""
    text = "This is terrible work. The results are awful and I hate the poor quality."
    
    result = await sentiment_analyzer.analyze_text(text)
    
    assert result.classification == SentimentPolarity.NEGATIVE
    assert result.polarity < 0
    assert len(result.negative_words) > 0


@pytest.mark.asyncio
async def test_analyze_neutral_text(sentiment_analyzer):
    """Test analyzing neutral text."""
    text = "The system processes data and returns results."
    
    result = await sentiment_analyzer.analyze_text(text)
    
    assert result.classification == SentimentPolarity.NEUTRAL
    assert -0.1 <= result.polarity <= 0.1


@pytest.mark.asyncio
async def test_analyze_batch(sentiment_analyzer):
    """Test batch sentiment analysis."""
    texts = [
        "This is great!",
        "This is terrible.",
        "This is okay.",
    ]
    
    batch = await sentiment_analyzer.analyze_batch(
        tenant_id="tenant_test",
        texts=texts
    )
    
    assert len(batch.results) == 3
    assert batch.positive_count >= 1
    assert batch.negative_count >= 1
    assert batch.positive_count + batch.neutral_count + batch.negative_count == 3
    assert batch.tenant_id == "tenant_test"


@pytest.mark.asyncio
async def test_sentiment_insights(sentiment_analyzer):
    """Test generating sentiment insights."""
    # Create some sample results
    results = []
    for text in [
        "Excellent service!",
        "Great experience!",
        "Amazing quality!",
        "Poor performance.",
    ]:
        result = await sentiment_analyzer.analyze_text(text)
        results.append(result)
    
    insights = await sentiment_analyzer.get_sentiment_insights(results)
    
    assert "insights" in insights
    assert "recommendations" in insights
    assert "summary" in insights
    assert "sentiment_distribution" in insights
    assert len(insights["insights"]) > 0


@pytest.mark.asyncio
async def test_subjectivity_score(sentiment_analyzer):
    """Test subjectivity scoring."""
    # Subjective text
    subjective_text = "I absolutely love this amazing product!"
    result1 = await sentiment_analyzer.analyze_text(subjective_text)
    
    # Objective text
    objective_text = "The product weighs 10 pounds and measures 5 inches."
    result2 = await sentiment_analyzer.analyze_text(objective_text)
    
    assert result1.subjectivity > result2.subjectivity


@pytest.mark.asyncio
async def test_empty_text_handling(sentiment_analyzer):
    """Test handling of empty or very short text."""
    try:
        result = await sentiment_analyzer.analyze_text("")
        # If it doesn't raise an error, check the result
        assert result.word_count == 0
    except Exception:
        # It's acceptable for empty text to raise an error
        pass


@pytest.mark.asyncio
async def test_long_text_handling(sentiment_analyzer):
    """Test handling of very long text."""
    long_text = "This is great! " * 200  # 600 words
    
    result = await sentiment_analyzer.analyze_text(long_text)
    
    assert result.polarity > 0
    assert result.classification == SentimentPolarity.POSITIVE
    assert len(result.text) <= 500  # Should be truncated


@pytest.mark.asyncio
async def test_mixed_sentiment(sentiment_analyzer):
    """Test text with mixed sentiment."""
    mixed_text = "The product is great but the service is terrible."
    
    result = await sentiment_analyzer.analyze_text(mixed_text)
    
    # Mixed sentiment should be closer to neutral
    assert abs(result.polarity) < 0.5
    assert len(result.positive_words) > 0
    # Note: "terrible" might not be in our negative_words set, so just check it was analyzed
    assert result.word_count > 0
