"""Data serialization utilities."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel

from ..core.logging_config import get_logger
from ..memory.interfaces import MemoryEntry, MemoryType

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format string.

    Args:
    dt: Datetime object

    Returns:
    ISO format datetime string
    """
    return dt.isoformat()


def deserialize_datetime(dt_str: str) -> datetime:
    """Deserialize ISO format string to datetime.

    Args:
    dt_str: ISO format datetime string

    Returns:
    Datetime object
    """
    return datetime.fromisoformat(dt_str)


def serialize_to_json(obj: Union[BaseModel, Dict[str, Any], List[Any]]) -> str:
    """Serialize object to JSON string.

    Args:
    obj: Object to serialize

    Returns:
    JSON string
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump_json()
    return json.dumps(obj)


def deserialize_from_json(
    json_str: str, model_class: Optional[Type[T]] = None
) -> Union[Dict[str, Any], T]:
    """Deserialize JSON string to object.

    Args:
    json_str: JSON string
    model_class: Optional Pydantic model class to deserialize into

    Returns:
    Deserialized object
    """
    data = json.loads(json_str)
    if model_class is not None:
        return model_class.model_validate(data)
    return cast(Dict[str, Any], data)


def memory_entry_to_dict(entry: MemoryEntry) -> Dict[str, Any]:
    """Convert MemoryEntry to dictionary.

    Args:
    entry: Memory entry

    Returns:
    Dictionary representation
    """
    return {
        "id": entry.id,
        "content": entry.content,
        "metadata": entry.metadata,
        "memory_type": entry.memory_type.value,
        "timestamp": serialize_datetime(entry.timestamp),
        "ttl": entry.ttl,
        "embedding": entry.embedding,
        "tags": entry.tags,
        "priority": entry.priority,
    }


def dict_to_memory_entry(data: Dict[str, Any]) -> MemoryEntry:
    """Convert dictionary to MemoryEntry.

    Args:
    data: Dictionary data

    Returns:
    Memory entry
    """
    # Handle memory type
    memory_type_value = data.get("memory_type")
    memory_type = None
    if isinstance(memory_type_value, str):
        memory_type = MemoryType(memory_type_value)
    elif isinstance(memory_type_value, MemoryType):
        memory_type = memory_type_value
    else:
        # Default to CACHE if not specified
        memory_type = MemoryType.CACHE

    # Handle timestamp
    timestamp_value = data.get("timestamp")
    timestamp = None
    if isinstance(timestamp_value, str):
        timestamp = deserialize_datetime(timestamp_value)
    elif isinstance(timestamp_value, datetime):
        timestamp = timestamp_value
    else:
        # Default to current time if not specified
        timestamp = datetime.now().astimezone()

    # Convert metadata from string if needed
    metadata = data.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse metadata JSON: {metadata}")
            metadata = {}

    return MemoryEntry(
        id=data["id"],
        content=data["content"],
        metadata=metadata,
        memory_type=memory_type,
        timestamp=timestamp,
        ttl=data.get("ttl"),
        embedding=data.get("embedding"),
        tags=data.get("tags", []),
        priority=data.get("priority", 0),
    )
