"""Tests for memory service."""

from unittest.mock import AsyncMock, patch

import pytest

from agentic_workflow.core.interfaces import ComponentStatus
from agentic_workflow.memory.interfaces import MemoryResult
from agentic_workflow.memory.service import MemoryService


class TestMemoryService:
    """Test memory service functionality."""

    @pytest.fixture
    def service(self):
        """Create memory service fixture."""
        return MemoryService()

    @pytest.mark.asyncio
    async def test_initialize(self, service):
        """Test service initialization."""
        await service.initialize()
        assert service.initialized
        assert service.status == ComponentStatus.READY

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """Test initialization failure."""
        with patch.object(
            service.memory_manager, "initialize", side_effect=Exception("Test error")
        ):
            with pytest.raises(Exception):
                await service.initialize()
        assert not service.initialized
        assert service.status == ComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_start(self, service):
        """Test service start."""
        await service.start()
        assert service.status == ComponentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_uninitialized(self, service):
        """Test starting uninitialized service."""
        with patch.object(service, "initialize", side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                await service.start()
        assert service.status == ComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_stop(self, service):
        """Test service stop."""
        await service.initialize()
        await service.stop()
        assert service.status == ComponentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_stop_error(self, service):
        """Test stop with error."""
        await service.initialize()
        with patch.object(
            service.memory_manager, "close", side_effect=Exception("Test error")
        ):
            await service.stop()
        assert service.status == ComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check."""
        await service.initialize()

        # Mock memory manager health check
        service.memory_manager.health_check = AsyncMock(
            return_value={"store1": True, "store2": True}
        )

        response = await service.health_check()
        assert response.success
        assert response.data["status"] == "healthy"
        assert "stores" in response.data
        assert "component_status" in response.data

    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, service):
        """Test health check when not initialized."""
        response = await service.health_check()
        assert not response.success
        assert "not initialized" in response.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, service):
        """Test health check with degraded status."""
        await service.initialize()

        # Mock memory manager health check with some stores unhealthy
        service.memory_manager.health_check = AsyncMock(
            return_value={"store1": True, "store2": False}
        )

        response = await service.health_check()
        assert not response.success
        assert response.data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_process_request_store(self, service):
        """Test store request processing."""
        await service.initialize()

        # Mock memory manager store
        service.memory_manager.store = AsyncMock(return_value="test_entry_id")

        request = {
            "action": "store",
            "parameters": {
                "content": "test_content",
                "memory_type": "short_term",
                "metadata": {"source": "test"},
                "tags": ["test"],
            },
        }

        response = await service.process_request(request)
        assert response.success
        assert response.data["entry_id"] == "test_entry_id"
        service.memory_manager.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_request_retrieve(self, service):
        """Test retrieve request processing."""
        await service.initialize()

        # Mock memory manager retrieve
        mock_result = MemoryResult(
            entries=[],  # Empty list of entries is valid
            total_count=0,
            query_time=0.0,
            similarity_scores=[],  # Empty list of scores is valid
        )
        service.memory_manager.retrieve = AsyncMock(return_value=mock_result)

        request = {
            "action": "retrieve",
            "parameters": {
                "memory_type": "short_term",
                "content": "test query",
                "limit": 10,
            },
        }

        response = await service.process_request(request)
        assert response.success
        assert "entries" in response.data
        assert "total_count" in response.data
        service.memory_manager.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_request_similarity_search(self, service):
        """Test similarity search request processing."""
        await service.initialize()

        # Mock memory manager search_similar
        mock_result = MemoryResult(
            entries=[],  # Empty list of entries is valid
            total_count=0,
            query_time=0.0,
            similarity_scores=[],  # Empty list of scores is valid
        )
        service.memory_manager.search_similar = AsyncMock(return_value=mock_result)

        request = {
            "action": "search_similar",
            "parameters": {
                "content": "test query",
                "limit": 10,
                "threshold": 0.7,
            },
        }

        response = await service.process_request(request)
        assert response.success
        assert "entries" in response.data
        assert "total_count" in response.data
        service.memory_manager.search_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_request_invalid_action(self, service):
        """Test invalid action handling."""
        await service.initialize()

        request = {
            "action": "invalid_action",
            "parameters": {},
        }

        response = await service.process_request(request)
        assert not response.success
        assert "unknown action" in response.error.lower()

    @pytest.mark.asyncio
    async def test_process_request_missing_parameters(self, service):
        """Test missing parameters handling."""
        await service.initialize()

        request = {
            "action": "store",
            "parameters": {},
        }

        response = await service.process_request(request)
        assert not response.success
        assert "content is required" in response.error.lower()
