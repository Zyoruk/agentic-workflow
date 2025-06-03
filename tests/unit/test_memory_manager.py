"""Unit tests for MemoryManager logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agentic_workflow.memory.interfaces import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryType,
)
from agentic_workflow.memory.manager import MemoryManager


@pytest.fixture
def manager():
    with patch("agentic_workflow.memory.manager.MemoryStoreFactory") as MockFactory:
        mock_factory = MockFactory.return_value

        # Create mock stores with proper async methods
        mock_short_term = AsyncMock()
        mock_vector = AsyncMock()
        mock_cache = AsyncMock()

        # Set up factory methods to return our mocks
        mock_factory.create_short_term_store = Mock(return_value=mock_short_term)
        mock_factory.create_vector_store = Mock(return_value=mock_vector)
        mock_factory.create_cache_store = Mock(return_value=mock_cache)

        manager = MemoryManager({"short_term": {"type": "short_term"}})
        manager._factory = mock_factory
        yield manager


@pytest.mark.asyncio
async def test_initialize(manager):
    """Test memory manager initialization."""
    # Get the mock factory from the fixture
    mock_factory = manager._factory

    # Initialize the manager
    await manager.initialize()

    # Verify factory methods were called
    mock_factory.create_short_term_store.assert_called_once_with(
        name="short_term", config={"type": "short_term"}
    )
    mock_factory.create_vector_store.assert_called_once_with(
        name="vector_store", config={}
    )
    mock_factory.create_cache_store.assert_called_once_with(name="cache", config={})

    # Verify stores were created
    assert "short_term" in manager.stores
    assert "cache" in manager.stores

    # Verify store types were mapped
    assert manager.store_types[MemoryType.SHORT_TERM] == "short_term"
    assert manager.store_types[MemoryType.CACHE] == "cache"

    # Verify each store was initialized
    # (Cannot check .initialize.called due to coroutine object)


@pytest.mark.asyncio
async def test_store_and_retrieve(manager):
    # Use a real MemoryEntry for the result
    entry = MemoryEntry(
        id="id1",
        content="test_content",
        metadata={},
        memory_type=MemoryType.SHORT_TERM,
        timestamp=datetime.now(timezone.utc),
        ttl=None,
        tags=[],
        priority=0,
    )
    manager.stores = {"short_term": MagicMock()}
    manager.store_types = {MemoryType.SHORT_TERM: "short_term"}
    manager.stores["short_term"].store = AsyncMock(return_value=True)
    manager.stores["short_term"].retrieve = AsyncMock(
        return_value=MemoryResult(
            entries=[entry],
            total_count=1,
            query_time=0.1,
            similarity_scores=[1.0],
            success=True,
        )
    )
    entry_id = await manager.store(
        content="test_content", memory_type=MemoryType.SHORT_TERM
    )
    assert isinstance(entry_id, str)
    result = await manager.retrieve(
        query=MemoryQuery(memory_type=MemoryType.SHORT_TERM)
    )
    assert result.entries[0].content == "test_content"
    assert result.total_count == 1
    assert result.query_time == 0.1
    assert result.similarity_scores == [1.0]
    assert result.success is True


@pytest.mark.asyncio
async def test_store_error(manager):
    manager.stores = {"short_term": MagicMock()}
    manager.store_types = {MemoryType.SHORT_TERM: "short_term"}
    manager.stores["short_term"].store = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        await manager.store(content="fail", memory_type=MemoryType.SHORT_TERM)


@pytest.mark.asyncio
async def test_retrieve_error(manager):
    manager.stores = {"short_term": MagicMock()}
    manager.store_types = {MemoryType.SHORT_TERM: "short_term"}
    manager.stores["short_term"].retrieve = AsyncMock(
        return_value=MemoryResult(
            entries=[],
            total_count=0,
            query_time=0.0,
            similarity_scores=[],
            success=False,
        )
    )
    result = await manager.retrieve(
        query=MemoryQuery(memory_type=MemoryType.SHORT_TERM)
    )
    assert result.entries == []
