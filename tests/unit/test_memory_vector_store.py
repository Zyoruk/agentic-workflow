import pytest

from agentic_workflow.memory.vector_store import VectorStore


class DummyVectorStore(VectorStore):
    async def add(self, *args, **kwargs):
        return True

    async def search(self, *args, **kwargs):
        return []

    async def delete(self, *args, **kwargs):
        return True

    async def health_check(self):
        return True

    async def clear(self, *args, **kwargs):
        return True

    async def close(self):
        return True

    async def create_embedding(self, *args, **kwargs):
        return [0.0]

    async def get_stats(self):
        return {}

    async def retrieve(self, *args, **kwargs):
        return []

    async def semantic_search(self, *args, **kwargs):
        return []

    async def similarity_search(self, *args, **kwargs):
        return []

    async def store(self, *args, **kwargs):
        return True

    async def update(self, *args, **kwargs):
        return True


@pytest.mark.unit
def test_vector_store_methods():
    store = DummyVectorStore("dummy", {})
    assert store.name == "dummy"
