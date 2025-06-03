"""Unit tests for short-term memory implementation."""

from datetime import datetime, timedelta, timezone

import pytest

from agentic_workflow.memory.interfaces import (
    MemoryEntry,
    MemoryQuery,
    MemoryStats,
    MemoryType,
)
from agentic_workflow.memory.short_term import ContextWindow, ShortTermMemory


@pytest.fixture
def memory_entry() -> MemoryEntry:
    """Create a test memory entry."""
    return MemoryEntry(
        id="test-entry",
        content="Test content",
        metadata={"type": "test"},
        timestamp=datetime.now(timezone.utc),
        memory_type=MemoryType.SHORT_TERM,
    )


@pytest.fixture
def context_window() -> ContextWindow:
    """Create a test context window."""
    return ContextWindow("test-window", max_size=3)


@pytest.fixture
def short_term_memory() -> ShortTermMemory:
    """Create a test short-term memory instance."""
    return ShortTermMemory(
        name="test-memory",
        config={
            "max_total_entries": 10,
            "default_window_size": 3,
            "entry_ttl": 3600,
            "window_ttl": 7200,
            "cleanup_interval": 1,
        },
    )


@pytest.mark.unit
class TestContextWindow:
    """Test context window functionality."""

    def test_add_entry(
        self, context_window: ContextWindow, memory_entry: MemoryEntry
    ) -> None:
        """Test adding an entry to the context window."""
        context_window.add_entry(memory_entry)
        assert context_window.size() == 1
        assert context_window.get_entry(memory_entry.id) == memory_entry

    def test_add_entry_capacity(self, context_window: ContextWindow) -> None:
        """Test context window capacity management."""
        # Add entries up to capacity
        for i in range(4):  # One more than max_size
            entry = MemoryEntry(
                id=f"entry-{i}",
                content=f"Content {i}",
                timestamp=datetime.now(timezone.utc),
                memory_type=MemoryType.SHORT_TERM,
            )
            context_window.add_entry(entry)

        # Should maintain max_size
        assert context_window.size() == 3
        # Oldest entry should be removed
        assert context_window.get_entry("entry-0") is None
        # Newest entry should be present
        assert context_window.get_entry("entry-3") is not None

    def test_remove_entry(
        self, context_window: ContextWindow, memory_entry: MemoryEntry
    ) -> None:
        """Test removing an entry from the context window."""
        context_window.add_entry(memory_entry)
        assert context_window.remove_entry(memory_entry.id) is True
        assert context_window.size() == 0
        assert context_window.remove_entry("nonexistent") is False

    def test_get_all_entries(self, context_window: ContextWindow) -> None:
        """Test retrieving all entries from the context window."""
        entries = [
            MemoryEntry(
                id=f"entry-{i}",
                content=f"Content {i}",
                timestamp=datetime.now(timezone.utc),
                memory_type=MemoryType.SHORT_TERM,
            )
            for i in range(3)
        ]
        for entry in entries:
            context_window.add_entry(entry)

        all_entries = context_window.get_all_entries()
        assert len(all_entries) == 3
        assert all(entry in all_entries for entry in entries)

    def test_is_expired(self, context_window: ContextWindow) -> None:
        """Test window expiration check."""
        # Not expired
        assert context_window.is_expired(3600) is False

        # Make it expired
        context_window.last_accessed = datetime.now(timezone.utc) - timedelta(hours=2)
        assert context_window.is_expired(3600) is True


@pytest.mark.unit
class TestShortTermMemory:
    """Test short-term memory functionality."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(
        self, short_term_memory: ShortTermMemory, memory_entry: MemoryEntry
    ) -> None:
        """Test storing and retrieving entries."""
        # Store entry
        assert await short_term_memory.store(memory_entry) is True

        # Retrieve by ID
        query = MemoryQuery(entry_id=memory_entry.id)
        result = await short_term_memory.retrieve(query)
        assert result.success is True
        assert len(result.entries) == 1
        assert result.entries[0].id == memory_entry.id

    @pytest.mark.asyncio
    async def test_retrieve_by_metadata(
        self, short_term_memory: ShortTermMemory
    ) -> None:
        """Test retrieving entries by metadata."""
        # Store entries with different metadata
        entries = [
            MemoryEntry(
                id=f"entry-{i}",
                content=f"Content {i}",
                metadata={"type": "test", "category": f"cat-{i}"},
                timestamp=datetime.now(timezone.utc),
                memory_type=MemoryType.SHORT_TERM,
            )
            for i in range(3)
        ]
        for entry in entries:
            await short_term_memory.store(entry)

        # Query by metadata_filters
        query = MemoryQuery(metadata_filters={"type": "test", "category": "cat-1"})
        result = await short_term_memory.retrieve(query)
        assert result.success is True
        assert len(result.entries) == 1
        assert result.entries[0].id == "entry-1"

    @pytest.mark.asyncio
    async def test_update_entry(
        self, short_term_memory: ShortTermMemory, memory_entry: MemoryEntry
    ) -> None:
        """Test updating an entry."""
        # Store initial entry
        await short_term_memory.store(memory_entry)

        # Update entry
        updates = {"content": "Updated content", "metadata": {"type": "updated"}}
        assert await short_term_memory.update(memory_entry.id, updates) is True

        # Verify update
        query = MemoryQuery(entry_id=memory_entry.id)
        result = await short_term_memory.retrieve(query)
        assert result.entries[0].content == "Updated content"
        assert result.entries[0].metadata["type"] == "updated"

    @pytest.mark.asyncio
    async def test_delete_entry(
        self, short_term_memory: ShortTermMemory, memory_entry: MemoryEntry
    ) -> None:
        """Test deleting an entry."""
        # Store entry
        await short_term_memory.store(memory_entry)

        # Delete entry
        assert await short_term_memory.delete(memory_entry.id) is True

        # Verify deletion
        query = MemoryQuery(entry_id=memory_entry.id)
        result = await short_term_memory.retrieve(query)
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_clear_memory(self, short_term_memory: ShortTermMemory) -> None:
        """Test clearing memory."""
        # Store entries
        entries = [
            MemoryEntry(
                id=f"entry-{i}",
                content=f"Content {i}",
                timestamp=datetime.now(timezone.utc),
                memory_type=MemoryType.SHORT_TERM,
            )
            for i in range(3)
        ]
        for entry in entries:
            await short_term_memory.store(entry)

        # Clear memory
        assert await short_term_memory.clear() is True

        # Verify all entries are gone
        query = MemoryQuery()
        result = await short_term_memory.retrieve(query)
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, short_term_memory: ShortTermMemory) -> None:
        """Test getting memory statistics."""
        # Store some entries
        for i in range(3):
            entry = MemoryEntry(
                id=f"entry-{i}",
                content=f"Content {i}",
                timestamp=datetime.now(timezone.utc),
                memory_type=MemoryType.SHORT_TERM,
            )
            await short_term_memory.store(entry)

        # Get stats
        stats = await short_term_memory.get_stats()
        assert isinstance(stats, MemoryStats)
        assert stats.total_entries == 3
        assert stats.total_stores == 3
        assert stats.total_retrievals >= 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, short_term_memory: ShortTermMemory) -> None:
        """Test cleanup of expired entries."""
        # Store entry with short TTL
        entry = MemoryEntry(
            id="expired-entry",
            content="Expired content",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            memory_type=MemoryType.SHORT_TERM,
            ttl=3600,  # 1 hour TTL
        )
        await short_term_memory.store(entry)

        # Trigger cleanup
        await short_term_memory._cleanup_expired()

        # Verify entry is removed
        query = MemoryQuery(entry_id=entry.id)
        result = await short_term_memory.retrieve(query)
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_context_window_operations(
        self, short_term_memory: ShortTermMemory
    ) -> None:
        """Test context window operations."""
        # Create context window
        window_id = "test-window"
        window = await short_term_memory.get_context_window(window_id)
        assert window is not None

        # Add entry to window
        entry = MemoryEntry(
            id="window-entry",
            content="Window content",
            timestamp=datetime.now(timezone.utc),
            memory_type=MemoryType.SHORT_TERM,
        )
        window.add_entry(entry)

        # List windows
        windows = await short_term_memory.list_context_windows()
        assert window_id in windows

    @pytest.mark.asyncio
    async def test_close(self, short_term_memory: ShortTermMemory) -> None:
        """Test closing the memory store."""
        # Start cleanup task
        short_term_memory._start_cleanup_task()
        assert short_term_memory._cleanup_task is not None

        # Close memory store
        await short_term_memory.close()
        assert short_term_memory._cleanup_task is None
        assert short_term_memory._cleanup_started is False
