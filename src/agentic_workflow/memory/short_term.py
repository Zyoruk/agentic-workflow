"""Short-term memory implementation for the agentic workflow system."""

import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.logging_config import get_logger
from .interfaces import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryStore,
    MemoryType,
)

logger = get_logger(__name__)


class ContextWindow:
    """Manages a context window of memory entries."""

    def __init__(self, window_id: str, max_size: int = 100):
        """Initialize context window.

        Args:
            window_id: Unique identifier for the window
            max_size: Maximum number of entries in the window
        """
        self.window_id = window_id
        self.max_size = max_size
        self.entries: OrderedDict[str, MemoryEntry] = OrderedDict()
        self.created_at = datetime.now(timezone.utc)
        self.last_accessed = datetime.now(timezone.utc)

    def add_entry(self, entry: MemoryEntry) -> None:
        """Add an entry to the context window."""
        # Remove if already exists to update position
        if entry.id in self.entries:
            del self.entries[entry.id]

        # Add to end
        self.entries[entry.id] = entry
        self.last_accessed = datetime.now(timezone.utc)

        # Ensure capacity
        while len(self.entries) > self.max_size:
            self.entries.popitem(last=False)  # Remove oldest

    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get an entry from the context window."""
        entry = self.entries.get(entry_id)
        if entry:
            # Move to end (most recently accessed)
            del self.entries[entry_id]
            self.entries[entry_id] = entry
            self.last_accessed = datetime.now(timezone.utc)
        return entry

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the context window."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self.last_accessed = datetime.now(timezone.utc)
            return True
        return False

    def get_all_entries(self) -> List[MemoryEntry]:
        """Get all entries in the context window."""
        return list(self.entries.values())

    def size(self) -> int:
        """Get the number of entries in the window."""
        return len(self.entries)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the window has expired."""
        return (
            datetime.now(timezone.utc) - self.last_accessed
        ).total_seconds() > ttl_seconds


class ShortTermMemory(MemoryStore):
    """Short-term memory implementation with context windows and LRU eviction."""

    def __init__(
        self, name: str = "short_term_memory", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize short-term memory.

        Args:
            name: Name of the memory store
            config: Configuration parameters
        """
        super().__init__(name, config)

        # Configuration
        config = config or {}
        self.max_total_entries = config.get("max_total_entries", 1000)
        self.default_window_size = config.get("default_window_size", 100)
        self.entry_ttl = config.get("entry_ttl", 3600)  # 1 hour default
        self.window_ttl = config.get("window_ttl", 7200)  # 2 hours default
        self.cleanup_interval = config.get("cleanup_interval", 300)  # 5 minutes default

        # Storage
        self.context_windows: Dict[str, ContextWindow] = {}
        self.entries: OrderedDict[str, MemoryEntry] = OrderedDict()

        # Statistics
        self.total_stores = 0
        self.total_retrievals = 0
        self.cache_hits = 0
        self.last_cleanup = datetime.now(timezone.utc)

        # Cleanup task (will be created when needed)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_started = False

        logger.info(f"Initialized short-term memory: {name}")

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task if not already started."""
        if not self._cleanup_started:
            try:
                # Only create task if we have a running event loop
                loop = asyncio.get_running_loop()
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = loop.create_task(self._cleanup_loop())
                    self._cleanup_started = True
                    logger.debug("Started cleanup task")
            except RuntimeError:
                # No running event loop, task will be created when store is first used
                logger.debug(
                    "No running event loop, cleanup task will be created on first use"
                )
                pass
            except Exception as e:
                logger.error(f"Failed to start cleanup task: {e}")
                self._cleanup_started = False
                self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries and windows."""
        try:
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    logger.debug("Cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup loop: {e}")
                    # Don't break on error, just log and continue
                    await asyncio.sleep(1)  # Brief pause before retrying
        finally:
            self._cleanup_started = False
            self._cleanup_task = None
            logger.debug("Cleanup task stopped")

    async def _cleanup_expired(self) -> None:
        """Clean up expired entries and context windows."""
        now = datetime.now(timezone.utc)
        expired_entries = []
        expired_windows = []

        # Find expired entries
        for entry_id, entry in self.entries.items():
            if entry.ttl and (now - entry.timestamp).total_seconds() > entry.ttl:
                expired_entries.append(entry_id)
            elif (now - entry.timestamp).total_seconds() > self.entry_ttl:
                expired_entries.append(entry_id)

        # Find expired windows
        for window_id, window in self.context_windows.items():
            if window.is_expired(self.window_ttl):
                expired_windows.append(window_id)

        # Remove expired entries
        for entry_id in expired_entries:
            if entry_id in self.entries:
                self.entries.pop(entry_id)
                # Remove from all windows
                for window in self.context_windows.values():
                    window.remove_entry(entry_id)

        # Remove expired windows
        for window_id in expired_windows:
            if window_id in self.context_windows:
                self.context_windows.pop(window_id)

        if expired_entries or expired_windows:
            logger.info(
                f"Cleaned up {len(expired_entries)} expired entries "
                f"and {len(expired_windows)} expired windows"
            )

        self.last_cleanup = now

    def _ensure_capacity(self) -> None:
        """Ensure we don't exceed maximum capacity."""
        while len(self.entries) >= self.max_total_entries:
            # Remove oldest entry
            oldest_key = next(iter(self.entries))
            self.entries.pop(oldest_key)

            # Remove from all windows
            for window in self.context_windows.values():
                window.remove_entry(oldest_key)

            logger.debug(f"Evicted entry due to capacity: {oldest_key}")

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry in short-term memory.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Start cleanup task if not already started
            self._start_cleanup_task()

            self._ensure_capacity()

            # Store in main collection
            self.entries[entry.id] = entry

            # Add to appropriate context window
            window_id = entry.metadata.get("context_window", "default")
            if window_id not in self.context_windows:
                window_size = entry.metadata.get(
                    "window_size", self.default_window_size
                )
                self.context_windows[window_id] = ContextWindow(window_id, window_size)

            self.context_windows[window_id].add_entry(entry)

            self.total_stores += 1

            logger.debug(f"Stored entry in short-term memory: {entry.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store entry {entry.id}: {e}")
            return False

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query.

        Args:
            query: Query parameters

        Returns:
            Query results
        """
        start_time = time.time()
        self.total_retrievals += 1

        try:
            matching_entries = []

            # Filter by context window if specified
            window_id = query.metadata_filters.get("context_window")
            if window_id and window_id in self.context_windows:
                candidates = self.context_windows[window_id].get_all_entries()
            else:
                candidates = list(self.entries.values())

            # Apply filters
            for entry in candidates:
                if self._matches_query(entry, query):
                    matching_entries.append(entry)

            # Sort by priority and timestamp
            matching_entries.sort(
                key=lambda e: (-e.priority, e.timestamp), reverse=True
            )

            # Apply limit
            limited_entries = matching_entries[: query.limit]

            query_time = time.time() - start_time

            if limited_entries:
                self.cache_hits += 1

            logger.debug(
                f"Retrieved {len(limited_entries)} entries in {query_time:.3f}s"
            )

            return MemoryResult(
                entries=limited_entries,
                total_count=len(matching_entries),
                query_time=query_time,
                similarity_scores=[],
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to retrieve entries: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    def _matches_query(self, entry: MemoryEntry, query: MemoryQuery) -> bool:
        """Check if an entry matches the query criteria."""
        # Memory type filter
        if query.memory_type and entry.memory_type != query.memory_type:
            return False

        # Content filter (simple text search)
        if query.content and query.content.lower() not in entry.content.lower():
            return False

        # Tags filter
        if query.tags:
            if not any(tag in entry.tags for tag in query.tags):
                return False

        # Metadata filters
        for key, value in query.metadata_filters.items():
            if key == "context_window":
                continue  # Handled separately
            if entry.metadata.get(key) != value:
                return False

        # Time range filter
        if query.time_range:
            start_time, end_time = query.time_range
            if not (start_time <= entry.timestamp <= end_time):
                return False

        return True

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry.

        Args:
            entry_id: ID of the entry to update
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            if entry_id not in self.entries:
                return False

            entry = self.entries[entry_id]

            # Update fields
            for field, value in updates.items():
                if hasattr(entry, field):
                    setattr(entry, field, value)

            # Update in context windows
            for window in self.context_windows.values():
                if entry_id in window.entries:
                    window.entries[entry_id] = entry

            logger.debug(f"Updated entry: {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if entry_id not in self.entries:
                return False

            # Remove from main collection
            self.entries.pop(entry_id)

            # Remove from all context windows
            for window in self.context_windows.values():
                window.remove_entry(entry_id)

            logger.debug(f"Deleted entry: {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type

        Returns:
            True if successful, False otherwise
        """
        try:
            if memory_type is None:
                # Clear everything
                self.entries.clear()
                self.context_windows.clear()
                logger.info("Cleared all short-term memory")
            else:
                # Clear entries of specific type
                to_remove = [
                    entry_id
                    for entry_id, entry in self.entries.items()
                    if entry.memory_type == memory_type
                ]

                for entry_id in to_remove:
                    await self.delete(entry_id)

                logger.info(f"Cleared {len(to_remove)} entries of type {memory_type}")

            return True

        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics.

        Returns:
            Memory statistics
        """
        try:
            # Calculate basic stats
            total_entries = len(self.entries)
            memory_usage = sum(len(str(e)) for e in self.entries.values())
            hit_rate = (
                self.cache_hits / self.total_retrievals
                if self.total_retrievals > 0
                else 0.0
            )

            # Count entries by type
            entries_by_type: Dict[str, int] = {}
            for entry in self.entries.values():
                memory_type = entry.memory_type.value
                entries_by_type[memory_type] = entries_by_type.get(memory_type, 0) + 1

            return MemoryStats(
                total_entries=total_entries,
                memory_usage=memory_usage,
                hit_rate=hit_rate,
                average_retrieval_time=0.0,  # Not tracked
                entries_by_type=entries_by_type,
                total_stores=self.total_stores,
                total_retrievals=self.total_retrievals,
            )

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return MemoryStats(
                total_entries=0,
                memory_usage=0,
                hit_rate=0.0,
                average_retrieval_time=0.0,
                entries_by_type={},
                total_stores=0,
                total_retrievals=0,
            )

    async def health_check(self) -> bool:
        """Check if the memory store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if cleanup task is running
            if self._cleanup_task and self._cleanup_task.done():
                self._start_cleanup_task()

            # Check memory usage
            stats = await self.get_stats()
            if stats.total_entries > self.max_total_entries * 1.1:  # 10% buffer
                logger.warning("Short-term memory usage exceeds safe limits")
                return False

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_context_window(self, window_id: str) -> Optional[ContextWindow]:
        """Get a context window by ID."""
        if window_id not in self.context_windows:
            self.context_windows[window_id] = ContextWindow(
                window_id, max_size=self.default_window_size
            )
        return self.context_windows[window_id]

    async def list_context_windows(self) -> List[str]:
        """List all context window IDs.

        Returns:
            List of context window IDs
        """
        return list(self.context_windows.keys())

    async def close(self) -> None:
        """Close the memory store and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error cancelling cleanup task: {e}")

        self.entries.clear()
        self.context_windows.clear()
        self._cleanup_started = False
        self._cleanup_task = None

        logger.info("Short-term memory closed")

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Vector embedding
        """
        # Short-term memory doesn't create real embeddings, just a placeholder
        # In a real implementation, you would use a proper embedding model
        logger.warning("Short-term memory doesn't support real embeddings")
        return [0.0] * 10  # Return a placeholder embedding

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search using vector embeddings.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Similar memory entries
        """
        # Short-term memory doesn't support real vector similarity search
        # In a real implementation, you would compute cosine similarity
        logger.warning("Short-term memory doesn't support vector similarity search")

        # Return most recent entries as fallback
        entries = list(self.entries.values())[:limit]
        return MemoryResult(
            entries=entries,
            total_count=len(entries),
            query_time=0.0,
            similarity_scores=[0.0] * len(entries),
        )
