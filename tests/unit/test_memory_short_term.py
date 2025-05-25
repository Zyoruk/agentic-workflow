import pytest

from agentic_workflow.memory.short_term import ShortTermMemory


@pytest.mark.unit
def test_short_term_memory_init():
    store = ShortTermMemory("short", {})
    assert store.name == "short"
