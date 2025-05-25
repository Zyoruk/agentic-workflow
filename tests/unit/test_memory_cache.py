import pytest

from agentic_workflow.memory.cache import CacheMemoryStore


@pytest.mark.unit
def test_cache_memory_store_init():
    cache = CacheMemoryStore("cache", {})
    assert cache.name == "cache_memory_store" or cache.name == "cache"
