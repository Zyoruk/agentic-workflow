"""Unit tests for serialization utilities."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from pydantic import BaseModel

from agentic_workflow.memory import MemoryEntry, MemoryType
from agentic_workflow.utils.serialization import (
    deserialize_datetime,
    deserialize_from_json,
    dict_to_memory_entry,
    memory_entry_to_dict,
    serialize_datetime,
    serialize_to_json,
)


class TestPydanticModel(BaseModel):
    """Test Pydantic model for serialization."""

    name: str
    value: int
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class TestSerializationUtils:
    """Tests for serialization utilities."""

    @pytest.fixture
    def sample_datetime(self) -> datetime:
        """Create a sample datetime."""
        return datetime(2023, 5, 23, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def sample_memory_entry(self) -> MemoryEntry:
        """Create a sample memory entry."""
        return MemoryEntry(
            id="test-123",
            content="Test content",
            memory_type=MemoryType.CACHE,
            metadata={"test": "value", "number": 42},
            timestamp=datetime(2023, 5, 23, 12, 0, 0, tzinfo=timezone.utc),
            tags=["test", "cache"],
            priority=10,
            ttl=300,
        )

    @pytest.fixture
    def sample_model(self) -> TestPydanticModel:
        """Create a sample Pydantic model."""
        return TestPydanticModel(
            name="test", value=42, tags=["a", "b"], metadata={"key": "value"}
        )

    @pytest.mark.unit
    def test_serialize_datetime(self, sample_datetime: datetime) -> None:
        """Test serializing datetime to ISO format string."""
        dt_str = serialize_datetime(sample_datetime)

        assert dt_str == "2023-05-23T12:00:00+00:00"
        assert isinstance(dt_str, str)

    @pytest.mark.unit
    def test_deserialize_datetime(self) -> None:
        """Test deserializing ISO format string to datetime."""
        dt_str = "2023-05-23T12:00:00+00:00"
        dt = deserialize_datetime(dt_str)

        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 5
        assert dt.day == 23
        assert dt.hour == 12
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.tzinfo is not None

    @pytest.mark.unit
    def test_serialize_to_json_dict(self) -> None:
        """Test serializing dictionary to JSON."""
        data = {"name": "test", "value": 42, "nested": {"key": "value"}}
        json_str = serialize_to_json(data)

        assert isinstance(json_str, str)
        # Verify can be parsed back to same structure
        parsed = json.loads(json_str)
        assert parsed == data

    @pytest.mark.unit
    def test_serialize_to_json_list(self) -> None:
        """Test serializing list to JSON."""
        data = [1, 2, {"name": "test"}]
        json_str = serialize_to_json(data)

        assert isinstance(json_str, str)
        # Verify can be parsed back to same structure
        parsed = json.loads(json_str)
        assert parsed == data

    @pytest.mark.unit
    def test_serialize_to_json_pydantic(self, sample_model: TestPydanticModel) -> None:
        """Test serializing Pydantic model to JSON."""
        json_str = serialize_to_json(sample_model)

        assert isinstance(json_str, str)
        # Verify can be parsed back to same structure
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
        assert parsed["tags"] == ["a", "b"]
        assert parsed["metadata"] == {"key": "value"}

    @pytest.mark.unit
    def test_deserialize_from_json_dict(self) -> None:
        """Test deserializing JSON to dictionary."""
        json_str = '{"name":"test","value":42,"nested":{"key":"value"}}'
        data = deserialize_from_json(json_str)

        assert isinstance(data, dict)
        assert data["name"] == "test"
        assert data["value"] == 42
        assert data["nested"]["key"] == "value"

    @pytest.mark.unit
    def test_deserialize_from_json_model(self) -> None:
        """Test deserializing JSON to Pydantic model."""
        json_str = (
            '{"name":"test","value":42,"tags":["a","b"],"metadata":{"key":"value"}}'
        )
        model = deserialize_from_json(json_str, TestPydanticModel)

        assert isinstance(model, TestPydanticModel)
        assert model.name == "test"
        assert model.value == 42
        assert model.tags == ["a", "b"]
        assert model.metadata == {"key": "value"}

    @pytest.mark.unit
    def test_memory_entry_to_dict(self, sample_memory_entry: MemoryEntry) -> None:
        """Test converting MemoryEntry to dictionary."""
        entry_dict = memory_entry_to_dict(sample_memory_entry)

        assert isinstance(entry_dict, dict)
        assert entry_dict["id"] == "test-123"
        assert entry_dict["content"] == "Test content"
        assert entry_dict["memory_type"] == "cache"
        assert entry_dict["metadata"] == {"test": "value", "number": 42}
        assert entry_dict["timestamp"] == "2023-05-23T12:00:00+00:00"
        assert entry_dict["tags"] == ["test", "cache"]
        assert entry_dict["priority"] == 10
        assert entry_dict["ttl"] == 300

    @pytest.mark.unit
    def test_dict_to_memory_entry(self) -> None:
        """Test converting dictionary to MemoryEntry."""
        entry_dict = {
            "id": "test-123",
            "content": "Test content",
            "memory_type": "cache",
            "metadata": {"test": "value", "number": 42},
            "timestamp": "2023-05-23T12:00:00+00:00",
            "tags": ["test", "cache"],
            "priority": 10,
            "ttl": 300,
        }

        entry = dict_to_memory_entry(entry_dict)

        assert isinstance(entry, MemoryEntry)
        assert entry.id == "test-123"
        assert entry.content == "Test content"
        assert entry.memory_type == MemoryType.CACHE
        assert entry.metadata == {"test": "value", "number": 42}
        assert entry.timestamp.isoformat() == "2023-05-23T12:00:00+00:00"
        assert entry.tags == ["test", "cache"]
        assert entry.priority == 10
        assert entry.ttl == 300

    @pytest.mark.unit
    def test_dict_to_memory_entry_with_string_metadata(self) -> None:
        """Test converting dictionary with string metadata to MemoryEntry."""
        entry_dict = {
            "id": "test-123",
            "content": "Test content",
            "memory_type": "cache",
            "metadata": '{"test":"value","number":42}',
            "timestamp": "2023-05-23T12:00:00+00:00",
        }

        entry = dict_to_memory_entry(entry_dict)

        assert isinstance(entry, MemoryEntry)
        assert entry.metadata == {"test": "value", "number": 42}
