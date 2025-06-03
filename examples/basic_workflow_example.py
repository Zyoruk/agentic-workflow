#!/usr/bin/env python3
"""Basic workflow example demonstrating the core architecture."""

import asyncio
from typing import Any, Dict

from agentic_workflow.core import (
    Service,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
    get_logger,
    setup_logging,
)

logger = get_logger(__name__)


class DataProcessorService(Service):
    """Sample service that processes data."""

    async def initialize(self) -> None:
        """Initialize the data processor."""
        logger.info("Initializing data processor service")
        self.processed_items = 0

    async def start(self) -> None:
        """Start the data processor."""
        logger.info("Starting data processor service")

    async def stop(self) -> None:
        """Stop the data processor."""
        logger.info("Stopping data processor service")

    async def health_check(self) -> ServiceResponse:
        """Check service health."""
        return ServiceResponse(
            success=True,
            data={"status": "healthy", "processed_items": self.processed_items},
        )

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a request."""
        action = request.get("action")
        parameters = request.get("parameters", {})

        logger.info_with_data(  # type: ignore[attr-defined]
            f"Processing request: {action}", action=action, parameters=parameters
        )

        if action == "validate":
            return await self._validate_data(parameters)
        elif action == "transform":
            return await self._transform_data(parameters)
        elif action == "save":
            return await self._save_data(parameters)
        else:
            return ServiceResponse(success=False, error=f"Unknown action: {action}")

    async def _validate_data(self, parameters: Dict[str, Any]) -> ServiceResponse:
        """Validate input data."""
        data = parameters.get("data", [])

        if not isinstance(data, list):
            return ServiceResponse(success=False, error="Data must be a list")

        if len(data) == 0:
            return ServiceResponse(success=False, error="Data cannot be empty")

        return ServiceResponse(
            success=True, data={"validation_result": "passed", "item_count": len(data)}
        )

    async def _transform_data(self, parameters: Dict[str, Any]) -> ServiceResponse:
        """Transform the data."""
        data = parameters.get("data", [])
        transformation = parameters.get("transformation", "uppercase")

        if transformation == "uppercase":
            transformed_data = [str(item).upper() for item in data]
        elif transformation == "lowercase":
            transformed_data = [str(item).lower() for item in data]
        else:
            transformed_data = data

        return ServiceResponse(
            success=True,
            data={
                "transformed_data": transformed_data,
                "transformation_applied": transformation,
            },
        )

    async def _save_data(self, parameters: Dict[str, Any]) -> ServiceResponse:
        """Save the data (mock implementation)."""
        data = parameters.get("data", [])
        destination = parameters.get("destination", "default")

        # Mock save operation
        self.processed_items += len(data)

        logger.info_with_data(  # type: ignore[attr-defined]
            f"Saved {len(data)} items to {destination}",
            item_count=len(data),
            destination=destination,
            total_processed=self.processed_items,
        )

        return ServiceResponse(
            success=True,
            data={
                "saved_items": len(data),
                "destination": destination,
                "total_processed": self.processed_items,
            },
        )


class NotificationService(Service):
    """Sample service that sends notifications."""

    async def initialize(self) -> None:
        """Initialize the notification service."""
        logger.info("Initializing notification service")
        self.notifications_sent = 0

    async def start(self) -> None:
        """Start the notification service."""
        logger.info("Starting notification service")

    async def stop(self) -> None:
        """Stop the notification service."""
        logger.info("Stopping notification service")

    async def health_check(self) -> ServiceResponse:
        """Check service health."""
        return ServiceResponse(
            success=True,
            data={"status": "healthy", "notifications_sent": self.notifications_sent},
        )

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a notification request."""
        action = request.get("action")
        parameters = request.get("parameters", {})

        if action == "send_notification":
            return await self._send_notification(parameters)
        else:
            return ServiceResponse(success=False, error=f"Unknown action: {action}")

    async def _send_notification(self, parameters: Dict[str, Any]) -> ServiceResponse:
        """Send a notification (mock implementation)."""
        message = parameters.get("message", "Default notification")
        recipients = parameters.get("recipients", ["admin"])

        # Mock notification sending
        self.notifications_sent += len(recipients)

        logger.info(
            f"Sent notification to {len(recipients)} recipients",
            extra={
                "notification_message": message,
                "recipients": recipients,
                "total_sent": self.notifications_sent,
            }
        )

        return ServiceResponse(
            success=True,
            data={
                "message_sent": message,
                "recipients": recipients,
                "total_sent": self.notifications_sent,
            },
        )


async def create_sample_workflow() -> WorkflowDefinition:
    """Create a sample data processing workflow."""
    return WorkflowDefinition(
        id="data-processing-workflow",
        name="Data Processing Workflow",
        description="A sample workflow that validates, transforms, and saves data",
        steps=[
            WorkflowStep(
                id="validate-step",
                name="Validate Data",
                component="data-processor",
                action="validate",
                parameters={"data": ["hello", "world", "from", "agentic", "workflow"]},
            ),
            WorkflowStep(
                id="transform-step",
                name="Transform Data",
                component="data-processor",
                action="transform",
                parameters={
                    "data": ["hello", "world", "from", "agentic", "workflow"],
                    "transformation": "uppercase",
                },
                dependencies=["validate-step"],
            ),
            WorkflowStep(
                id="save-step",
                name="Save Data",
                component="data-processor",
                action="save",
                parameters={
                    "data": ["HELLO", "WORLD", "FROM", "AGENTIC", "WORKFLOW"],
                    "destination": "processed_data_store",
                },
                dependencies=["transform-step"],
            ),
            WorkflowStep(
                id="notify-step",
                name="Send Notification",
                component="notification-service",
                action="send_notification",
                parameters={
                    "message": "Data processing workflow completed successfully",
                    "recipients": ["admin", "data-team"],
                },
                dependencies=["save-step"],
            ),
        ],
        metadata={"created_by": "example_script", "environment": "development"},
    )


async def main() -> None:
    """Main function demonstrating the core architecture."""
    # Setup logging
    setup_logging()

    logger.info("Starting basic workflow example")

    try:
        # Create workflow engine
        engine = WorkflowEngine()

        # Create and register services
        data_processor = DataProcessorService("data-processor")
        notification_service = NotificationService("notification-service")

        engine.register_component(data_processor)
        engine.register_component(notification_service)

        # Use the lifecycle context manager
        async with engine.lifecycle():
            logger.info("Engine started, checking health...")

            # Check engine health
            health = await engine.health_check()
            logger.info_with_data(  # type: ignore[attr-defined]
                "Engine health check completed",
                healthy=health.success,
                components=(
                    list(health.data.get("components", {}).keys())
                    if health.data
                    else []
                ),
            )

            # Create and execute workflow
            workflow = await create_sample_workflow()

            logger.info("Executing sample workflow...")
            execution = await engine.execute_workflow(workflow)

            # Log execution results
            logger.info_with_data(  # type: ignore[attr-defined]
                "Workflow execution completed",
                execution_id=execution.id,
                status=execution.status,
                completed_steps=len(execution.completed_steps),
                failed_steps=len(execution.failed_steps),
                error=execution.error,
            )

            if execution.status == "completed":
                logger.info("✅ Workflow completed successfully!")

                # Final health check
                final_health = await engine.health_check()
                if final_health.data:
                    logger.info_with_data(  # type: ignore[attr-defined]
                        "Final system state", **final_health.data
                    )
            else:
                logger.error(f"❌ Workflow failed: {execution.error}")

    except Exception as e:
        logger.error_with_data(  # type: ignore[attr-defined]
            "Example execution failed", error=str(e), exc_info=True
        )
        raise

    logger.info("Basic workflow example completed")


if __name__ == "__main__":
    asyncio.run(main())
