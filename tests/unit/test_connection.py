import pytest

from agentic_workflow.utils.connection import ConnectionManager


class DummyConnectionManager(ConnectionManager):
    async def connect(self):
        return True

    async def disconnect(self):
        return True

    async def _check_connection_health(self):
        return True


@pytest.mark.unit
def test_connection_manager_status():
    mgr = DummyConnectionManager("dummy", {})
    status = mgr.get_status()
    assert status["name"] == "dummy"
    assert status["connected"] is False
    assert status["healthy"] is False
    assert status["error"] is None
