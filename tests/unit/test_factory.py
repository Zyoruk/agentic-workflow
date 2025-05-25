"""Unit tests for memory store factory."""

from unittest.mock import patch

import pytest

from agentic_workflow.memory import (
    CacheStore,
    MemoryStoreFactory,
    RedisCacheStore,
    ShortTermMemory,
)


class TestMemoryStoreFactory:
    """Tests for the MemoryStoreFactory."""

    @pytest.fixture
    def factory(self) -> MemoryStoreFactory:
        """Create a factory instance."""
        return MemoryStoreFactory()

    @pytest.mark.unit
    def test_create_short_term_store(self, factory: MemoryStoreFactory) -> None:
        """Test creating a short-term memory store."""
        store = factory.create_short_term_store(
            name="test_short_term", config={"max_total_entries": 100}
        )

        assert isinstance(store, ShortTermMemory)
        assert store.name == "test_short_term"
        assert store.config["max_total_entries"] == 100

    @pytest.mark.unit
    def test_create_cache_store(self, factory: MemoryStoreFactory) -> None:
        """Test creating a cache store."""
        store = factory.create_cache_store(
            name="test_cache", config={"url": "redis://localhost:6379/0"}
        )

        assert isinstance(store, RedisCacheStore)
        assert isinstance(store, CacheStore)
        assert store.name == "test_cache"
        assert store.config["url"] == "redis://localhost:6379/0"

    @pytest.mark.unit
    def test_create_vector_store_not_available(
        self, factory: MemoryStoreFactory
    ) -> None:
        """Test creating a vector store when not available."""
        # Mock VECTOR_STORE_AVAILABLE to False
        with patch("agentic_workflow.memory.factory.VECTOR_STORE_AVAILABLE", False):
            store = factory.create_vector_store(
                name="test_vector", config={"url": "http://localhost:8080"}
            )

            assert store is None

    @pytest.mark.unit
    def test_create_store_short_term(self, factory: MemoryStoreFactory) -> None:
        """Test creating a store by type (short_term)."""
        store = factory.create_store(
            store_type="short_term",
            name="test_short_term",
            config={"max_total_entries": 100},
        )

        assert isinstance(store, ShortTermMemory)
        assert store.name == "test_short_term"

    @pytest.mark.unit
    def test_create_store_cache(self, factory: MemoryStoreFactory) -> None:
        """Test creating a store by type (cache)."""
        store = factory.create_store(
            store_type="cache",
            name="test_cache",
            config={"url": "redis://localhost:6379/0"},
        )

        assert isinstance(store, RedisCacheStore)
        assert store.name == "test_cache"

    @pytest.mark.unit
    def test_create_store_vector_not_available(
        self, factory: MemoryStoreFactory
    ) -> None:
        """Test creating a store by type (vector) when not available."""
        # Mock VECTOR_STORE_AVAILABLE to False
        with patch("agentic_workflow.memory.factory.VECTOR_STORE_AVAILABLE", False):
            store = factory.create_store(
                store_type="vector",
                name="test_vector",
                config={"url": "http://localhost:8080"},
            )

            assert store is None

    @pytest.mark.unit
    def test_create_store_unknown_type(self, factory: MemoryStoreFactory) -> None:
        """Test creating a store with unknown type."""
        store = factory.create_store(
            store_type="unknown", name="test_unknown", config={}
        )

        assert store is None

    @pytest.mark.unit
    def test_create_store_with_exception(self, factory: MemoryStoreFactory) -> None:
        """Test creating a store when an exception occurs."""
        # Mock ShortTermMemory to raise exception
        with patch(
            "agentic_workflow.memory.factory.ShortTermMemory",
            side_effect=Exception("Test error"),
        ):
            store = factory.create_store(
                store_type="short_term", name="test_short_term", config={}
            )

            assert store is None
