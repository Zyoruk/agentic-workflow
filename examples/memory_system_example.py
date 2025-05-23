#!/usr/bin/env python3
"""Memory system example demonstrating the memory management foundation."""

import asyncio
from datetime import datetime

from agentic_workflow.core import get_logger, setup_logging
from agentic_workflow.memory import MemoryManager, MemoryQuery, MemoryType

logger = get_logger(__name__)


async def demonstrate_short_term_memory(memory_manager: MemoryManager) -> None:
    """Demonstrate short-term memory with context windows."""
    logger.info("=== Short-Term Memory Demonstration ===")

    # Store conversation context
    conversation_entries = [
        "User: Hello, I need help with Python programming",
        "Assistant: I'd be happy to help you with Python! What specific topic are you interested in?",
        "User: I want to learn about async programming",
        "Assistant: Async programming in Python is powerful for handling concurrent operations...",
        "User: Can you show me an example?",
    ]

    # Store entries in a conversation context window
    stored_ids = []
    for i, content in enumerate(conversation_entries):
        entry_id = await memory_manager.store(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            metadata={
                "context_window": "conversation_1",
                "turn": i + 1,
                "speaker": "User" if content.startswith("User:") else "Assistant",
            },
            tags=["conversation", "python", "async"],
            priority=5 if "example" in content.lower() else 1,
        )
        stored_ids.append(entry_id)
        logger.info(f"Stored conversation turn {i + 1}: {entry_id}")

    # Retrieve conversation history
    logger.info("\n--- Retrieving conversation history ---")
    result = await memory_manager.retrieve(
        memory_type=MemoryType.SHORT_TERM, tags=["conversation"], limit=10
    )

    logger.info(f"Retrieved {len(result.entries)} conversation entries:")
    for entry in result.entries:
        speaker = entry.metadata.get("speaker", "Unknown")
        turn = entry.metadata.get("turn", "?")
        logger.info(f"  Turn {turn} ({speaker}): {entry.content[:50]}...")

    # Query specific context window
    logger.info("\n--- Querying specific context window ---")
    context_result = await memory_manager.retrieve(
        query=MemoryQuery(
            memory_type=MemoryType.SHORT_TERM,
            metadata_filters={"context_window": "conversation_1"},
            limit=5,
        )
    )

    logger.info(f"Found {len(context_result.entries)} entries in conversation_1 window")

    # Update entry priority
    if stored_ids:
        await memory_manager.update(
            stored_ids[-1],  # Last entry
            {"priority": 10, "tags": ["conversation", "python", "async", "important"]},
            MemoryType.SHORT_TERM,
        )
        logger.info("Updated last entry with higher priority")


async def demonstrate_vector_memory(memory_manager: MemoryManager) -> None:
    """Demonstrate vector store for long-term semantic memory."""
    logger.info("\n=== Vector Memory Demonstration ===")

    # Store knowledge base entries
    knowledge_entries = [
        "Python is a high-level programming language with dynamic semantics",
        "Async programming allows concurrent execution of multiple tasks",
        "FastAPI is a modern web framework for building APIs with Python",
        "Machine learning involves algorithms that learn from data",
        "Neural networks are computing systems inspired by biological networks",
        "Docker containers provide lightweight virtualization for applications",
        "Kubernetes orchestrates containerized applications at scale",
        "REST APIs use HTTP methods for web service communication",
    ]

    stored_ids = []
    for i, content in enumerate(knowledge_entries):
        entry_id = await memory_manager.store(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            metadata={
                "domain": "programming" if i < 4 else "devops" if i >= 6 else "ai",
                "complexity": "beginner" if i % 2 == 0 else "intermediate",
                "source": "knowledge_base",
            },
            tags=["knowledge", "documentation"],
            priority=3,
        )
        stored_ids.append(entry_id)
        logger.info(f"Stored knowledge entry {i + 1}: {content[:30]}...")

    # Perform semantic similarity searches
    logger.info("\n--- Semantic similarity searches ---")

    search_queries = [
        "web development with Python",
        "containerization and deployment",
        "artificial intelligence and learning",
    ]

    for query_text in search_queries:
        logger.info(f"\nSearching for: '{query_text}'")

        # Note: This uses mock embeddings, so results may not be semantically meaningful
        # In production, you would use real embeddings from OpenAI, Sentence Transformers, etc.
        result = await memory_manager.search_similar(
            content=query_text,
            limit=3,
            threshold=0.1,  # Low threshold for mock embeddings
        )

        logger.info(f"Found {len(result.entries)} similar entries:")
        for i, entry in enumerate(result.entries):
            similarity = (
                result.similarity_scores[i]
                if i < len(result.similarity_scores)
                else 0.0
            )
            logger.info(f"  {i + 1}. (score: {similarity:.3f}) {entry.content[:50]}...")


async def demonstrate_cache_memory(memory_manager: MemoryManager) -> None:
    """Demonstrate cache for fast temporary storage."""
    logger.info("\n=== Cache Memory Demonstration ===")

    # Store session data
    session_data = [
        (
            "user_123",
            {
                "name": "Alice",
                "role": "developer",
                "last_active": datetime.now().isoformat(),
            },
        ),
        (
            "workspace_456",
            {
                "project": "agentic-workflow",
                "settings": {"theme": "dark", "auto_save": True},
            },
        ),
        (
            "temp_calc_789",
            {"operation": "fibonacci", "result": [1, 1, 2, 3, 5, 8, 13, 21]},
        ),
    ]

    logger.info("Storing session data in cache...")
    for key, data in session_data:
        success = await memory_manager.cache_set(key, data, ttl=300)  # 5 minutes TTL
        status = "✓" if success else "✗"
        logger.info(f"  {status} Cached {key}: {str(data)[:50]}...")

    # Retrieve cached data
    logger.info("\n--- Retrieving cached data ---")
    for key, _ in session_data:
        cached_value = await memory_manager.cache_get(key)
        if cached_value:
            logger.info(f"  Retrieved {key}: {str(cached_value)[:50]}...")
        else:
            logger.info(f"  Cache miss for {key}")

    # Store cache entries as memory entries
    logger.info("\n--- Storing cache entries as memory entries ---")
    cache_entries = []
    for key, data in session_data:
        entry_id = await memory_manager.store(
            content=f"Cached data for {key}: {str(data)}",
            memory_type=MemoryType.CACHE,
            metadata={"cache_key": key, "data_type": type(data).__name__},
            tags=["cache", "session"],
            ttl=600,  # 10 minutes
        )
        cache_entries.append(entry_id)
        logger.info(f"  Stored cache entry: {entry_id}")

    # Query cache entries
    cache_result = await memory_manager.retrieve(
        memory_type=MemoryType.CACHE, tags=["cache"], limit=10
    )

    logger.info(f"\nRetrieved {len(cache_result.entries)} cache memory entries")


async def demonstrate_cross_memory_operations(memory_manager: MemoryManager) -> None:
    """Demonstrate operations across multiple memory types."""
    logger.info("\n=== Cross-Memory Operations ===")

    # Store same concept in different memory types
    concept = "RESTful API design patterns"

    # Short-term: Recent discussion
    st_id = await memory_manager.store(
        content=f"User asked about {concept} in today's session",
        memory_type=MemoryType.SHORT_TERM,
        metadata={"session_id": "sess_001", "context": "discussion"},
        tags=["recent", "api", "discussion"],
    )

    # Long-term: Knowledge base
    lt_id = await memory_manager.store(
        content=f"{concept}: REST uses HTTP methods (GET, POST, PUT, DELETE) for resource manipulation",
        memory_type=MemoryType.LONG_TERM,
        metadata={"source": "documentation", "topic": "api_design"},
        tags=["knowledge", "api", "rest"],
    )

    # Cache: Quick reference
    cache_success = await memory_manager.cache_set(
        "api_patterns",
        {
            "REST": "Representational State Transfer",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "principles": ["stateless", "uniform_interface", "cacheable"],
        },
        ttl=3600,
    )

    logger.info(
        f"Stored concept across memories - ST: {st_id}, LT: {lt_id}, Cache: {cache_success}"
    )

    # Search across all memory types
    logger.info("\n--- Cross-memory search ---")
    all_results = await memory_manager.retrieve(content="API", limit=10)

    logger.info(f"Found {len(all_results.entries)} entries across all memory types:")
    memory_type_counts = {}
    for entry in all_results.entries:
        mem_type = entry.memory_type.value
        memory_type_counts[mem_type] = memory_type_counts.get(mem_type, 0) + 1
        logger.info(f"  [{mem_type}] {entry.content[:60]}...")

    logger.info(f"\nResults by memory type: {memory_type_counts}")


async def demonstrate_memory_statistics(memory_manager: MemoryManager) -> None:
    """Demonstrate memory system statistics and health monitoring."""
    logger.info("\n=== Memory Statistics & Health ===")

    # Get comprehensive statistics
    stats = await memory_manager.get_stats()

    logger.info("Memory system statistics:")
    logger.info(f"  Total operations: {stats['total_operations']}")
    logger.info(f"  Operations by type: {stats['operations_by_type']}")

    logger.info("\nPer-store statistics:")
    for store_name, store_stats in stats["stores"].items():
        if "error" in store_stats:
            logger.info(f"  {store_name}: Error - {store_stats['error']}")
        else:
            logger.info(f"  {store_name}:")
            logger.info(f"    Total entries: {store_stats['total_entries']}")
            logger.info(f"    Memory usage: {store_stats['memory_usage']} bytes")
            logger.info(f"    Hit rate: {store_stats['hit_rate']:.2%}")
            logger.info(f"    Entries by type: {store_stats['entries_by_type']}")

    # Check health status
    health_status = await memory_manager.health_check()

    logger.info("\nHealth status:")
    for store_name, is_healthy in health_status.items():
        status_icon = "🟢" if is_healthy else "🔴"
        logger.info(
            f"  {status_icon} {store_name}: {'Healthy' if is_healthy else 'Unhealthy'}"
        )

    overall_health = all(health_status.values())
    logger.info(
        f"\nOverall system health: {'🟢 Healthy' if overall_health else '🔴 Issues detected'}"
    )


async def main() -> None:
    """Main function demonstrating the memory management system."""
    # Setup logging
    setup_logging()

    logger.info("🧠 Starting Memory Management System Demonstration")

    # Configure memory manager
    memory_config = {
        "short_term": {
            "max_total_entries": 1000,
            "default_window_size": 50,
            "cleanup_interval": 60,  # 1 minute cleanup
        },
        "vector_store": {
            "url": "http://localhost:8080",  # Weaviate URL
            "class_name": "AgenticMemory",
        },
        "cache": {
            "url": "redis://localhost:6379",  # Redis URL
            "key_prefix": "agentic_memory:",
            "default_ttl": 3600,  # 1 hour default
        },
    }

    # Initialize memory manager
    memory_manager = MemoryManager(memory_config)

    try:
        logger.info("Initializing memory manager...")
        await memory_manager.initialize()

        # Run demonstrations
        await demonstrate_short_term_memory(memory_manager)
        await demonstrate_vector_memory(memory_manager)
        await demonstrate_cache_memory(memory_manager)
        await demonstrate_cross_memory_operations(memory_manager)
        await demonstrate_memory_statistics(memory_manager)

        logger.info("\n🎉 Memory system demonstration completed successfully!")

        # Show final stats
        final_stats = await memory_manager.get_stats()
        logger.info(f"\nFinal operation count: {final_stats['total_operations']}")

    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        logger.info("\nCleaning up memory manager...")
        await memory_manager.close()
        logger.info("Memory manager closed.")


if __name__ == "__main__":
    asyncio.run(main())
