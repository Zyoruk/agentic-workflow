"""Vector store implementation using Weaviate."""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from weaviate import WeaviateClient
from weaviate.collections.classes.config import DataType, Property
from weaviate.collections.classes.filters import Filter

from ..core.config import get_config
from ..core.logging_config import get_logger
from .interfaces import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
    VectorStore,
)

logger = get_logger(__name__)


class WeaviateVectorStore(VectorStore):
    """Weaviate-based vector store for long-term memory.

    This implementation supports Weaviate v4+ and uses LangChain for embeddings when available.

    To use LangChain embeddings:
    1. Install the optional dependency: `pip install agentic-workflow[embedding]`
    2. Set the OpenAI API key in your configuration or environment variable

    Example config:
    ```python
    config = {
    "url": "http://localhost:8080",  # Weaviate URL
    "auth_config": {"api_key": "your-api-key"},  # Optional Weaviate auth
    "openai_api_key": "your-openai-key",  # For LangChain embeddings
    "batch_size": 10  # Optional batch processing size
    }
    ```"""

    def __init__(
        self,
        name: str = "weaviate_vector_store",
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize vector store.

        Args:
        name: Name of the vector store
        config: Configuration parameters
        """
        super().__init__(name, config)

        # Configuration
        app_config = get_config()
        self.url = self.config.get("url", app_config.database.weaviate_url)
        self.api_key = self.config.get("api_key", app_config.database.weaviate_api_key)
        self.class_name = self.config.get("class_name", "MemoryEntry")
        self.vector_dim = int(self.config.get("vector_dim", 1536))
        self.batch_size = int(self.config.get("batch_size", 100))
        self.timeout = int(self.config.get("timeout", 60))
        self.provider = self.config.get("provider", "weaviate")
        self.store_type = self.config.get("store_type", "remote")

        # Client
        self.client: Optional[WeaviateClient] = None

        # LangChain embeddings
        self.openai_api_key = self.config.get(
            "openai_api_key", app_config.llm.openai_api_key
        )
        self.embedding_model = None
        if self.provider != "mock":
            try:
                self.embedding_model = OpenAIEmbeddings(
                    api_key=self.openai_api_key, model="text-embedding-ada-002"
                )
                logger.info("Initialized LangChain OpenAI embeddings")
            except Exception as e:
                logger.error(f"Failed to initialize LangChain embeddings: {e}")
                self.embedding_model = None

        # Statistics
        self.total_stores = 0
        self.total_queries = 0
        self.total_deletes = 0

        logger.info(f"Initialized vector store: {name}")

    async def _connect(self) -> bool:
        """Connect to Weaviate instance.

        Returns:
            True if connection successful, False otherwise
        """
        if self.provider == "mock" or self.store_type == "local":
            logger.info("Using mock vector store - no connection needed")
            return True

        try:
            # Create client
            self.client = WeaviateClient(self.url)

            # Test connection
            if self.client is not None and self.client.is_live():
                logger.info(f"Connected to Weaviate at {self.url}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False

    async def _ensure_client(self) -> bool:
        """Ensure Weaviate client is connected.

        Returns:
            True if client is available, False otherwise
        """
        if self.client is None:
            return await self._connect()
        return True

    async def _create_schema(self) -> bool:
        """Create Weaviate schema if it doesn't exist.

        Returns:
            True if schema created or already exists, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False
            # v4: list all collections (returns list of str)
            collections = self.client.collections.list_all()
            if self.class_name in collections:
                return True
            # v4: create collection using Property
            self.client.collections.create(
                name=self.class_name,
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="memory_type", data_type=DataType.TEXT),
                    Property(name="timestamp", data_type=DataType.DATE),
                    Property(name="metadata", data_type=DataType.TEXT),
                    Property(name="tags", data_type=DataType.TEXT_ARRAY),
                    Property(name="priority", data_type=DataType.NUMBER),
                ],
            )
            logger.info(f"Created Weaviate collection: {self.class_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return False

    def _serialize_entry(self, entry: MemoryEntry) -> Dict[str, Any]:
        """Serialize memory entry to Weaviate object."""
        return {
            "content": entry.content,
            "memory_type": entry.memory_type.value,
            "timestamp": entry.timestamp.isoformat(),
            "metadata": json.dumps(entry.metadata),
            "tags": entry.tags,
            "priority": entry.priority,
        }

    def _deserialize_entry(self, data: Any) -> Optional[MemoryEntry]:
        """Deserialize Weaviate object to memory entry."""
        try:
            d = dict(data)
            return MemoryEntry(
                id=d.get("id", ""),
                content=d["content"],
                metadata=json.loads(d["metadata"]),
                memory_type=MemoryType(d["memory_type"]),
                timestamp=datetime.fromisoformat(d["timestamp"]),
                embedding=d.get("vector", []),
                tags=d.get("tags", []),
                priority=d.get("priority", 0),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize entry: {e}")
            return None

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.provider == "mock" or self.store_type == "local":
                # Mock storage - just increment counter
                self.total_stores += 1
                logger.debug(f"Mock stored entry in vector store: {entry.id}")
                return True

            if not await self._ensure_client() or self.client is None:
                return False

            # Ensure schema exists
            if not await self._create_schema():
                return False

            # Generate embedding using LangChain if not provided
            if (
                not entry.embedding or len(entry.embedding) == 0
            ) and self.embedding_model is not None:
                try:
                    entry.embedding = self.embedding_model.embed_query(entry.content)
                    logger.debug(
                        f"Generated embedding for entry using LangChain: {entry.id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to generate embedding with LangChain: {e}")

            # Prepare data
            data = self._serialize_entry(entry)
            vector = entry.embedding if entry.embedding else None

            # Store in Weaviate
            self.client.collections.get(self.class_name).data.insert(
                properties=data,
                vector=vector,
            )

            self.total_stores += 1
            logger.debug(f"Stored entry in vector store: {entry.id}")
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
        self.total_queries += 1

        try:
            if not await self._ensure_client() or self.client is None:
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            collection = self.client.collections.get(self.class_name)

            # Build query
            if hasattr(query, "embedding") and query.embedding:
                results = collection.query.near_vector(
                    near_vector=query.embedding,
                    limit=query.limit,
                )
            else:
                results = collection.query.bm25(
                    query=query.content or "",
                    limit=query.limit,
                )

            # Process results
            entries: List[MemoryEntry] = []
            similarity_scores: List[float] = []

            for item in results.objects:
                entry = self._deserialize_entry(item.properties)
                if entry:
                    entries.append(entry)
                    similarity_scores.append(
                        item.score if hasattr(item, "score") else 0.0
                    )

            query_time = time.time() - start_time

            logger.debug(
                f"Retrieved {len(entries)} entries from vector store in {query_time:.3f}s"
            )

            return MemoryResult(
                entries=entries,
                total_count=len(entries),
                query_time=query_time,
                similarity_scores=similarity_scores,
            )

        except Exception as e:
            logger.error(f"Failed to retrieve vector entries: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry.

        Args:
            entry_id: ID of the entry to update
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            collection = self.client.collections.get(self.class_name)

            # Update fields
            collection.data.update(uuid=entry_id, properties=updates)

            logger.debug(f"Updated entry in vector store: {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update vector entry: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            collection = self.client.collections.get(self.class_name)
            collection.data.delete_by_id(entry_id)

            self.total_deletes += 1
            logger.debug(f"Deleted entry from vector store: {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vector entry: {e}")
            return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False
            collection = self.client.collections.get(self.class_name)
            if memory_type is None:
                # v4: delete all objects in collection (must use a filter that matches all)
                collection.data.delete_many(
                    where=Filter.by_property("content").is_none(False)
                )
                await self._create_schema()
            else:
                # v4: delete by filter
                filter_ = Filter.by_property("memory_type").equal(memory_type.value)
                collection.data.delete_many(where=filter_)
            logger.info(
                f"Cleared vector store entries{f' of type {memory_type}' if memory_type else ''}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return False

    async def get_stats(self) -> MemoryStats:
        """Get vector store statistics.

        Returns:
            Vector store statistics
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return MemoryStats(
                    total_entries=0,
                    memory_usage=0,
                    hit_rate=0.0,
                    average_retrieval_time=0.0,
                    entries_by_type={},
                    total_stores=self.total_stores,
                    total_retrievals=self.total_queries,
                )
            collection = self.client.collections.get(self.class_name)

            # v4: count objects using aggregate
            total_entries = collection.aggregate.over_all(total_count=True)
            total_count = total_entries.total if hasattr(total_entries, "total") else 0

            # v4: group by memory_type using aggregate
            entries_by_type: Dict[str, int] = {}
            try:
                # Use aggregate to get counts by memory_type
                type_stats = collection.aggregate.over_all(
                    group_by="memory_type", total_count=True
                )

                if hasattr(type_stats, "groups"):
                    for group in type_stats.groups:
                        if hasattr(group, "groupedBy") and hasattr(
                            group.groupedBy, "value"
                        ):
                            mt = group.groupedBy.value
                            entries_by_type[mt] = (
                                group.total if hasattr(group, "total") else 0
                            )
            except Exception as e:
                logger.warning(f"Failed to get type statistics: {e}")
                # Fallback to empty dict if aggregation fails
                entries_by_type = {}

            return MemoryStats(
                total_entries=total_count,
                memory_usage=0,
                hit_rate=1.0,
                average_retrieval_time=0.0,
                entries_by_type=entries_by_type,
                total_stores=self.total_stores,
                total_retrievals=self.total_queries,
            )
        except Exception as e:
            logger.error(f"Failed to get vector stats: {e}")
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
        """Check if the vector store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False
            return bool(self.client.is_live())
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Vector embedding
        """
        try:
            # Use LangChain for embedding generation
            if self.embedding_model is not None:
                # LangChain's embed_query returns a list of floats
                embedding = self.embedding_model.embed_query(content)
                if isinstance(embedding, list) and all(
                    isinstance(x, float) for x in embedding
                ):
                    return embedding
                else:
                    logger.warning(
                        f"Unexpected embedding result format from LangChain: {type(embedding)}"
                    )
                    return []
            else:
                logger.warning(
                    "LangChain embedding model is not available. "
                    "Make sure to install langchain-openai and configure OpenAI API key."
                )
                return []

        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return []

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
        try:
            if self.provider == "mock" or self.store_type == "local":
                # Return empty but valid result in mock mode
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=True,
                )

            if not await self._ensure_client() or self.client is None:
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            # If query_embedding is empty and we have LangChain available, generate it
            if (
                not query_embedding or len(query_embedding) == 0
            ) and self.embedding_model is not None:
                # We need some text to generate embeddings from
                logger.warning(
                    "Query embedding is empty, but no query text is provided"
                )
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            collection = self.client.collections.get(self.class_name)
            results = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
            )

            entries: List[MemoryEntry] = []
            similarity_scores: List[float] = []

            for item in results.objects:
                entry = self._deserialize_entry(item.properties)
                if entry and hasattr(item, "score") and item.score >= threshold:
                    entries.append(entry)
                    similarity_scores.append(item.score)

            return MemoryResult(
                entries=entries,
                total_count=len(entries),
                query_time=0.0,
                similarity_scores=similarity_scores,
            )
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def semantic_search(
        self, query_text: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform semantic search using text query.

        Args:
            query_text: Text query to search for
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Similar memory entries
        """
        try:
            if self.provider == "mock" or self.store_type == "local":
                # Return empty but valid result in mock mode
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=True,
                )

            # Generate embedding from text using LangChain
            if not query_text or self.embedding_model is None:
                logger.warning(
                    "Cannot perform semantic search: query text is empty "
                    "or LangChain embeddings are not available"
                )
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            # Get embedding for the query text
            query_embedding = self.embedding_model.embed_query(query_text)

            # Use the embedding for similarity search
            return await self.similarity_search(
                query_embedding=query_embedding, limit=limit, threshold=threshold
            )

        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def close(self) -> None:
        """Close the vector store and cleanup resources."""
        self.client = None
        logger.info("Vector store closed")
