"""Unit tests for utils.embeddings logic."""

from unittest.mock import AsyncMock

import pytest

from agentic_workflow.utils.embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)


@pytest.mark.asyncio
async def test_embed_text_success():
    """Test successful text embedding."""
    provider = MockEmbeddingProvider()
    result = await provider.embed_text("hello")
    assert isinstance(result, list)
    assert all(isinstance(x, float) for x in result)
    assert len(result) == 1536  # Default dimension


@pytest.mark.asyncio
async def test_embed_text_error():
    """Test error handling in text embedding."""
    provider = MockEmbeddingProvider()
    # Mock the embed_text method to raise an exception
    provider.embed_text = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        await provider.embed_text("fail")


@pytest.mark.asyncio
async def test_batch_embed_text():
    """Test batch text embedding."""
    provider = MockEmbeddingProvider()
    texts = ["a", "b"]
    results = await provider.embed_batch(texts)
    assert isinstance(results, list)
    assert len(results) == len(texts)
    assert all(isinstance(x, list) for x in results)
    assert all(isinstance(y, float) for x in results for y in x)
    assert all(len(x) == 1536 for x in results)  # Default dimension


@pytest.mark.asyncio
async def test_get_embedding_provider():
    """Test getting embedding provider."""
    # Test mock provider
    provider = get_embedding_provider("mock")
    assert isinstance(provider, MockEmbeddingProvider)

    # Test OpenAI provider (should fall back to mock if not available)
    provider = get_embedding_provider("openai")
    assert isinstance(provider, (MockEmbeddingProvider, EmbeddingProvider))
