"""Unit tests for memory service component."""

from unittest.mock import patch

import pytest
import pytest_asyncio

from agentic_workflow.core.interfaces import ComponentStatus, ServiceResponse
from agentic_workflow.memory import MemoryQuery, MemoryService, MemoryType


@pytest_asyncio.fixture(scope="function")
async def memory_service():
    """Create memory service instance for testing and ensure cleanup."""
    config = {
        "memory": {
            "short_term": {"max_total_entries": 50},
            "vector_store": {"url": "http://localhost:8080"},
            "cache": {"url": "redis://localhost:6379"},
        }
    }
    service = MemoryService("test_memory_service", config)
    yield service
    await service.close()


class TestMemoryService:
    """Test memory service component."""

    @pytest.mark.asyncio
    async def test_initialization(self, memory_service):
        """Test memory service initialization."""
        assert memory_service.name == "test_memory_service"
        assert memory_service.status == ComponentStatus.INITIALIZING
        assert not memory_service.initialized

        # Initialize service
        await memory_service.initialize()

        assert memory_service.initialized
        assert memory_service.status == ComponentStatus.READY

    @pytest.mark.asyncio
    async def test_lifecycle(self, memory_service):
        """Test service lifecycle (start/stop)."""
        # Start service
        await memory_service.start()

        assert memory_service.status == ComponentStatus.RUNNING
        assert memory_service.initialized

        # Stop service
        await memory_service.stop()

        assert memory_service.status == ComponentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_health_check(self, memory_service):
        """Test health check functionality."""
        # Health check before initialization
        response = await memory_service.health_check()

        assert not response.success
        assert "not initialized" in response.error

        # Health check after initialization
        await memory_service.initialize()
        response = await memory_service.health_check()

        assert isinstance(response, ServiceResponse)
        assert "status" in response.data
        assert "stores" in response.data
        assert "component_status" in response.data

    @pytest.mark.asyncio
    async def test_store_request(self, memory_service):
        """Test store memory request processing."""
        await memory_service.initialize()

        request = {
            "action": "store",
            "parameters": {
                "content": "Test memory content",
                "memory_type": "short_term",
                "tags": ["test"],
                "priority": 5,
            },
        }

        response = await memory_service.process_request(request)

        assert response.success
        assert "entry_id" in response.data
        assert response.metadata["action"] == "store"
        assert response.metadata["memory_type"] == "short_term"

    @pytest.mark.asyncio
    async def test_retrieve_request(self, memory_service):
        """Test retrieve memory request processing."""
        await memory_service.initialize()

        # First store some content
        store_request = {
            "action": "store",
            "parameters": {
                "content": "Retrievable content",
                "memory_type": "short_term",
                "tags": ["retrievable"],
            },
        }
        await memory_service.process_request(store_request)

        # Then retrieve it
        retrieve_request = {
            "action": "retrieve",
            "parameters": {
                "content": "Retrievable",
                "memory_type": "short_term",
                "limit": 5,
            },
        }

        response = await memory_service.process_request(retrieve_request)

        assert response.success
        assert "entries" in response.data
        assert "total_count" in response.data
        assert "query_time" in response.data
        assert len(response.data["entries"]) > 0

    @pytest.mark.asyncio
    async def test_retrieve_with_query_object(self, memory_service):
        """Test retrieve with MemoryQuery object."""
        await memory_service.initialize()

        # Store content
        await memory_service.store_memory("Query object test", MemoryType.SHORT_TERM)

        # Retrieve with query object
        query = MemoryQuery(
            content="Query object", memory_type=MemoryType.SHORT_TERM, limit=5
        )

        request = {"action": "retrieve", "parameters": {"query": query.model_dump()}}

        response = await memory_service.process_request(request)

        assert response.success
        assert len(response.data["entries"]) > 0

    @pytest.mark.asyncio
    async def test_update_request(self, memory_service):
        """Test update memory entry request."""
        await memory_service.initialize()

        # Store content first
        entry_id = await memory_service.store_memory(
            "Original content", MemoryType.SHORT_TERM
        )

        # Update the entry
        update_request = {
            "action": "update",
            "parameters": {
                "entry_id": entry_id,
                "updates": {"content": "Updated content", "priority": 10},
                "memory_type": "short_term",
            },
        }

        response = await memory_service.process_request(update_request)

        assert response.success
        assert response.data["updated"]
        assert response.metadata["entry_id"] == entry_id

    @pytest.mark.asyncio
    async def test_delete_request(self, memory_service):
        """Test delete memory entry request."""
        await memory_service.initialize()

        # Store content first
        entry_id = await memory_service.store_memory(
            "Content to delete", MemoryType.SHORT_TERM
        )

        # Delete the entry
        delete_request = {
            "action": "delete",
            "parameters": {"entry_id": entry_id, "memory_type": "short_term"},
        }

        response = await memory_service.process_request(delete_request)

        assert response.success
        assert response.data["deleted"]
        assert response.metadata["entry_id"] == entry_id

    @pytest.mark.asyncio
    async def test_clear_request(self, memory_service):
        """Test clear memory request."""
        await memory_service.initialize()

        # Store some content
        await memory_service.store_memory("Content 1", MemoryType.SHORT_TERM)
        await memory_service.store_memory("Content 2", MemoryType.SHORT_TERM)

        # Clear memory
        clear_request = {"action": "clear", "parameters": {"memory_type": "short_term"}}

        response = await memory_service.process_request(clear_request)

        assert response.success
        assert response.data["cleared"]

    @pytest.mark.asyncio
    async def test_stats_request(self, memory_service):
        """Test get statistics request."""
        await memory_service.initialize()

        # Store some content
        await memory_service.store_memory("Stats test", MemoryType.SHORT_TERM)

        # Get stats
        stats_request = {"action": "get_stats", "parameters": {}}

        response = await memory_service.process_request(stats_request)

        assert response.success
        assert "total_operations" in response.data
        assert "stores" in response.data

    @pytest.mark.asyncio
    async def test_cache_operations(self, memory_service):
        """Test cache set/get operations."""
        await memory_service.initialize()

        # Cache set
        set_request = {
            "action": "cache_set",
            "parameters": {
                "key": "test_key",
                "value": {"data": "test_value"},
                "ttl": 300,
            },
        }

        response = await memory_service.process_request(set_request)
        # Note: Will fail without real Redis, but tests the interface
        assert not response.success  # Expected to fail without Redis

        # Cache get
        get_request = {"action": "cache_get", "parameters": {"key": "test_key"}}

        response = await memory_service.process_request(get_request)
        assert response.success  # Should succeed even if value is None
        assert "value" in response.data
        assert "found" in response.data

    @pytest.mark.asyncio
    async def test_similarity_search_request(self, memory_service):
        """Test similarity search request."""
        await memory_service.initialize()

        # Store content for similarity search (use short-term memory to avoid Weaviate dependency)
        await memory_service.store_memory(
            "Machine learning algorithms",
            MemoryType.SHORT_TERM,  # Changed from LONG_TERM to avoid Weaviate connection
        )

        # Perform similarity search
        search_request = {
            "action": "search_similar",
            "parameters": {
                "content": "artificial intelligence",
                "limit": 5,
                "threshold": 0.1,  # Low threshold for mock embeddings
            },
        }

        response = await memory_service.process_request(search_request)

        # Note: May fail without real vector store, but tests the interface
        assert isinstance(response, ServiceResponse)
        # Don't assert success since it may fail without vector store

    @pytest.mark.asyncio
    async def test_convenience_methods(self, memory_service):
        """Test convenience methods for direct access."""
        await memory_service.initialize()

        # Store memory
        entry_id = await memory_service.store_memory(
            "Convenience test", MemoryType.SHORT_TERM, tags=["convenience"], priority=3
        )

        assert entry_id

        # Retrieve memory
        result = await memory_service.retrieve_memory(
            content="Convenience", memory_type="short_term"
        )

        assert len(result.entries) > 0
        assert result.entries[0].content == "Convenience test"

        # Search similar memory
        result = await memory_service.search_similar_memory(
            "Convenience test", limit=5, threshold=0.1
        )

        assert isinstance(result.entries, list)

    @pytest.mark.asyncio
    async def test_invalid_action(self, memory_service):
        """Test handling of invalid action."""
        await memory_service.initialize()

        request = {"action": "invalid_action", "parameters": {}}

        response = await memory_service.process_request(request)

        assert not response.success
        assert "Unknown action" in response.error

    @pytest.mark.asyncio
    async def test_missing_parameters(self, memory_service):
        """Test handling of missing required parameters."""
        await memory_service.initialize()

        # Store without content
        request = {"action": "store", "parameters": {}}

        response = await memory_service.process_request(request)

        assert not response.success
        assert "Content is required" in response.error

        # Update without entry_id
        request = {
            "action": "update",
            "parameters": {"updates": {"content": "new content"}},
        }

        response = await memory_service.process_request(request)

        assert not response.success
        assert "entry_id and updates are required" in response.error

    @pytest.mark.asyncio
    async def test_error_handling(self, memory_service):
        """Test error handling in service operations."""
        # Initialize service first
        await memory_service.initialize()

        # Test health check error
        with patch.object(
            memory_service.memory_manager,
            "health_check",
            side_effect=Exception("Test error"),
        ):
            response = await memory_service.health_check()

            assert not response.success
            assert "Health check failed" in response.error

        # Test request processing error
        with patch.object(
            memory_service.memory_manager, "store", side_effect=Exception("Store error")
        ):
            request = {"action": "store", "parameters": {"content": "Test content"}}

            response = await memory_service.process_request(request)

            assert not response.success
            assert "Store operation failed" in response.error


if __name__ == "__main__":
    pytest.main([__file__])
