import pytest

from agentic_workflow.memory.interfaces import MemoryType


@pytest.mark.unit
def test_memory_type_enum():
    assert MemoryType.CACHE.value == "cache"
    assert MemoryType.SHORT_TERM.value == "short_term"
    assert MemoryType.LONG_TERM.value == "long_term"
