"""
WebSocket endpoint for real-time workflow execution monitoring.

This module provides WebSocket endpoints for streaming workflow execution
updates to clients in real-time. Clients can connect and receive live updates
about workflow progress, step completion, and results.

Sprint 5-6: Real-time execution monitoring
"""

from datetime import datetime, timezone
from typing import Dict, Set
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for workflow execution updates."""

    def __init__(self):
        # Maps workflow_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Maps execution_id -> workflow_id for routing
        self.execution_to_workflow: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """Register a new WebSocket connection for a workflow."""
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = set()
        self.active_connections[workflow_id].add(websocket)
        logger.info(f"WebSocket connected for workflow {workflow_id}. "
                   f"Total connections: {len(self.active_connections[workflow_id])}")

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        """Remove a WebSocket connection."""
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].discard(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
        logger.info(f"WebSocket disconnected for workflow {workflow_id}")

    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Send a message to all connections watching a workflow."""
        if workflow_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[workflow_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket, workflow_id)

    def register_execution(self, execution_id: str, workflow_id: str):
        """Map an execution to its workflow for message routing."""
        self.execution_to_workflow[execution_id] = workflow_id

    def get_workflow_for_execution(self, execution_id: str) -> str | None:
        """Get the workflow ID for an execution."""
        return self.execution_to_workflow.get(execution_id)


# Global connection manager instance
manager = ConnectionManager()


class ExecutionUpdate(BaseModel):
    """Model for workflow execution update messages."""
    type: str  # "started", "step_started", "step_completed", "completed", "failed"
    execution_id: str
    workflow_id: str
    timestamp: str
    data: dict


@router.websocket("/executions/{workflow_id}")
async def websocket_execution_endpoint(
    websocket: WebSocket,
    workflow_id: str,
):
    """
    WebSocket endpoint for real-time workflow execution updates.
    
    Clients connect to this endpoint to receive live updates about workflow
    execution progress. Updates include:
    - Workflow execution started
    - Individual step started/completed
    - Workflow execution completed
    - Execution failures/errors
    
    Example client usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/executions/wf_123');
    ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        console.log('Execution update:', update);
    };
    ```
    """
    await manager.connect(websocket, workflow_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Connected to workflow {workflow_id} execution stream"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (e.g., ping/pong)
                data = await websocket.receive_text()
                
                # Handle ping messages to keep connection alive
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for workflow {workflow_id}: {e}")
    finally:
        manager.disconnect(websocket, workflow_id)


async def send_execution_update(
    workflow_id: str,
    update_type: str,
    execution_id: str,
    data: dict
):
    """
    Send an execution update to all connected clients.
    
    This function should be called from workflow execution code to broadcast
    updates to connected clients.
    
    Args:
        workflow_id: ID of the workflow being executed
        update_type: Type of update (started, step_started, etc.)
        execution_id: ID of the execution
        data: Additional data about the update
    """
    update = ExecutionUpdate(
        type=update_type,
        execution_id=execution_id,
        workflow_id=workflow_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=data
    )
    
    await manager.broadcast_to_workflow(workflow_id, update.model_dump())
    logger.debug(f"Sent {update_type} update for execution {execution_id}")


# Export the manager and helper function
__all__ = ["router", "manager", "send_execution_update"]
