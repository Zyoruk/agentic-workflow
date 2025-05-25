import pytest

from agentic_workflow.memory.service import MemoryService


class DummyMemoryService(MemoryService):
    async def store(self, *args, **kwargs):
        return "id"

    async def retrieve(self, *args, **kwargs):
        return []

    async def update(self, *args, **kwargs):
        return True

    async def delete(self, *args, **kwargs):
        return True

    async def clear(self, *args, **kwargs):
        return True

    async def health_check(self):
        return True


@pytest.mark.unit
def test_memory_service_methods():
    service = DummyMemoryService("dummy", {})
    assert service.name == "dummy"
