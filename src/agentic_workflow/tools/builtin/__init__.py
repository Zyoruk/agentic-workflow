"""Built-in tools for the agentic workflow system."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from .. import Tool, ToolCapability


class FileSystemTool(Tool):
    """Tool for file system operations."""

    @classmethod
    def create_default(cls):
        """Create default instance of FileSystemTool."""
        capabilities = ToolCapability(
            name="File System Operations",
            description="Perform file and directory operations like read, write, list, create, delete",
            category="development",
            tags=["filesystem", "io", "files"],
            input_schema={
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "list", "create_dir", "delete"],
                },
                "path": {"type": "string"},
                "content": {"type": "string", "required": False},
            },
            output_schema={
                "success": {"type": "boolean"},
                "result": {"type": "string"},
                "error": {"type": "string", "required": False},
            },
        )
        return cls("filesystem_tool", capabilities)

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate filesystem tool inputs."""
        required_fields = ["operation", "path"]
        for field in required_fields:
            if field not in inputs:
                return False

        valid_operations = ["read", "write", "list", "create_dir", "delete"]
        return inputs["operation"] in valid_operations

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute filesystem operation."""
        operation = inputs["operation"]
        path = Path(inputs["path"])

        try:
            if operation == "read":
                if not path.exists():
                    return {"success": False, "error": f"File {path} does not exist"}
                content = path.read_text()
                return {"success": True, "result": content}

            elif operation == "write":
                content = inputs.get("content", "")
                path.write_text(content)
                return {
                    "success": True,
                    "result": f"Written {len(content)} characters to {path}",
                }

            elif operation == "list":
                if not path.exists():
                    return {
                        "success": False,
                        "error": f"Directory {path} does not exist",
                    }
                if not path.is_dir():
                    return {"success": False, "error": f"{path} is not a directory"}

                items = [item.name for item in path.iterdir()]
                return {"success": True, "result": json.dumps(items)}

            elif operation == "create_dir":
                path.mkdir(parents=True, exist_ok=True)
                return {"success": True, "result": f"Directory {path} created"}

            elif operation == "delete":
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
                else:
                    return {"success": False, "error": f"Path {path} does not exist"}
                return {"success": True, "result": f"Deleted {path}"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class TextProcessingTool(Tool):
    """Tool for text processing operations."""

    @classmethod
    def create_default(cls):
        """Create default instance of TextProcessingTool."""
        capabilities = ToolCapability(
            name="Text Processing",
            description="Process and manipulate text: count words, extract keywords, format, etc.",
            category="analysis",
            tags=["text", "nlp", "processing"],
            input_schema={
                "operation": {
                    "type": "string",
                    "enum": [
                        "word_count",
                        "line_count",
                        "extract_emails",
                        "uppercase",
                        "lowercase",
                    ],
                },
                "text": {"type": "string"},
            },
            output_schema={
                "success": {"type": "boolean"},
                "result": {"type": "object"},
                "error": {"type": "string", "required": False},
            },
        )
        return cls("text_processing_tool", capabilities)

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate text processing inputs."""
        required_fields = ["operation", "text"]
        for field in required_fields:
            if field not in inputs:
                return False

        valid_operations = [
            "word_count",
            "line_count",
            "extract_emails",
            "uppercase",
            "lowercase",
        ]
        return inputs["operation"] in valid_operations

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute text processing operation."""
        operation = inputs["operation"]
        text = inputs["text"]

        try:
            if operation == "word_count":
                words = len(text.split())
                return {"success": True, "result": {"word_count": words}}

            elif operation == "line_count":
                lines = len(text.splitlines())
                return {"success": True, "result": {"line_count": lines}}

            elif operation == "extract_emails":
                import re

                email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                emails = re.findall(email_pattern, text)
                return {"success": True, "result": {"emails": emails}}

            elif operation == "uppercase":
                return {"success": True, "result": {"text": text.upper()}}

            elif operation == "lowercase":
                return {"success": True, "result": {"text": text.lower()}}

        except Exception as e:
            return {"success": False, "error": str(e)}


class CommandExecutorTool(Tool):
    """Tool for executing system commands safely."""

    @classmethod
    def create_default(cls):
        """Create default instance of CommandExecutorTool."""
        capabilities = ToolCapability(
            name="Command Executor",
            description="Execute safe system commands and return output",
            category="development",
            tags=["command", "system", "execution"],
            input_schema={
                "command": {"type": "string"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "required": False,
                },
                "timeout": {"type": "number", "default": 30},
            },
            output_schema={
                "success": {"type": "boolean"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "return_code": {"type": "number"},
                "error": {"type": "string", "required": False},
            },
        )
        return cls("command_executor_tool", capabilities)

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate command executor inputs."""
        if "command" not in inputs:
            return False

        # Basic safety check - block dangerous commands
        dangerous_commands = ["rm", "rmdir", "del", "format", "fdisk", "mkfs"]
        command = inputs["command"].lower().strip()

        for dangerous in dangerous_commands:
            if command.startswith(dangerous):
                return False

        return True

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute system command safely."""
        command = inputs["command"]
        args = inputs.get("args", [])
        timeout = inputs.get("timeout", 30)

        try:
            # Build command list
            cmd_list = [command] + args

            # Execute command
            result = subprocess.run(
                cmd_list, capture_output=True, text=True, timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class DataAnalysisTool(Tool):
    """Tool for basic data analysis operations."""

    @classmethod
    def create_default(cls):
        """Create default instance of DataAnalysisTool."""
        capabilities = ToolCapability(
            name="Data Analysis",
            description="Perform basic data analysis: statistics, aggregations, filtering",
            category="analysis",
            tags=["data", "statistics", "analysis"],
            input_schema={
                "operation": {
                    "type": "string",
                    "enum": ["statistics", "filter", "aggregate", "transform"],
                },
                "data": {"type": "array"},
                "criteria": {"type": "object", "required": False},
            },
            output_schema={
                "success": {"type": "boolean"},
                "result": {"type": "object"},
                "error": {"type": "string", "required": False},
            },
        )
        return cls("data_analysis_tool", capabilities)

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate data analysis inputs."""
        required_fields = ["operation", "data"]
        for field in required_fields:
            if field not in inputs:
                return False

        valid_operations = ["statistics", "filter", "aggregate", "transform"]
        return inputs["operation"] in valid_operations

    async def execute(
        self, inputs: Dict[str, Any], context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute data analysis operation."""
        operation = inputs["operation"]
        data = inputs["data"]
        criteria = inputs.get("criteria", {})

        try:
            if operation == "statistics":
                # Calculate basic statistics for numeric data
                numeric_data = [x for x in data if isinstance(x, (int, float))]
                if not numeric_data:
                    return {"success": False, "error": "No numeric data found"}

                stats = {
                    "count": len(numeric_data),
                    "sum": sum(numeric_data),
                    "mean": sum(numeric_data) / len(numeric_data),
                    "min": min(numeric_data),
                    "max": max(numeric_data),
                }
                return {"success": True, "result": stats}

            elif operation == "filter":
                # Filter data based on criteria
                filter_key = criteria.get("key")
                filter_value = criteria.get("value")
                filter_op = criteria.get("operator", "equals")

                if not filter_key:
                    return {"success": False, "error": "Filter key not specified"}

                filtered_data = []
                for item in data:
                    if isinstance(item, dict) and filter_key in item:
                        item_value = item[filter_key]

                        if filter_op == "equals" and item_value == filter_value:
                            filtered_data.append(item)
                        elif filter_op == "greater" and item_value > filter_value:
                            filtered_data.append(item)
                        elif filter_op == "less" and item_value < filter_value:
                            filtered_data.append(item)

                return {
                    "success": True,
                    "result": {
                        "filtered_data": filtered_data,
                        "count": len(filtered_data),
                    },
                }

            elif operation == "aggregate":
                # Aggregate data by key
                group_key = criteria.get("group_by")
                agg_key = criteria.get("aggregate_key")
                agg_func = criteria.get("function", "sum")

                if not group_key or not agg_key:
                    return {
                        "success": False,
                        "error": "Group by and aggregate key required",
                    }

                groups = {}
                for item in data:
                    if isinstance(item, dict) and group_key in item and agg_key in item:
                        group_value = item[group_key]
                        agg_value = item[agg_key]

                        if group_value not in groups:
                            groups[group_value] = []
                        groups[group_value].append(agg_value)

                # Apply aggregation function
                result = {}
                for group, values in groups.items():
                    if agg_func == "sum":
                        result[group] = sum(values)
                    elif agg_func == "count":
                        result[group] = len(values)
                    elif agg_func == "average":
                        result[group] = sum(values) / len(values) if values else 0

                return {"success": True, "result": {"aggregated_data": result}}

            elif operation == "transform":
                # Transform data (simple operations)
                transform_type = criteria.get("type", "identity")

                if transform_type == "to_upper":
                    transformed = [
                        str(item).upper() if isinstance(item, str) else item
                        for item in data
                    ]
                elif transform_type == "to_lower":
                    transformed = [
                        str(item).lower() if isinstance(item, str) else item
                        for item in data
                    ]
                elif transform_type == "reverse":
                    transformed = list(reversed(data))
                else:
                    transformed = data

                return {"success": True, "result": {"transformed_data": transformed}}

        except Exception as e:
            return {"success": False, "error": str(e)}
