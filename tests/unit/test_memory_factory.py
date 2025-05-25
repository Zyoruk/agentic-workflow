import pytest

from agentic_workflow.memory.factory import MemoryStoreFactory


@pytest.mark.unit
def test_create_store_returns_none_on_invalid_type():
    factory = MemoryStoreFactory()
    store = factory.create_store("nonexistent", "name", {})
    assert store is None
