"""Example demonstrating memory service integration with the core workflow system."""

import asyncio
import logging
from typing import Any, Dict

from agentic_workflow.core.engine import WorkflowEngine
from agentic_workflow.core.interfaces import (
    Service,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowStep,
)
from agentic_workflow.memory.service import MemoryService
from agentic_workflow.memory.interfaces import MemoryType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessorService(Service):
    """Service that processes data and stores results in memory."""

    def __init__(self, name: str = "data_processor", config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.memory_service = None

    async def initialize(self) -> None:
        """Initialize the service."""
        logger.info("Initializing data processor service")

    async def start(self) -> None:
        """Start the service."""
        logger.info("Starting data processor service")

    async def stop(self) -> None:
        """Stop the service."""
        logger.info("Stopping data processor service")

    async def health_check(self) -> ServiceResponse:
        """Check service health."""
        return ServiceResponse(success=True, data={"status": "healthy"})

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a data processing request."""
        action = request.get("action")

        if action == "process_data":
            return await self._process_data(request.get("parameters", {}))
        elif action == "analyze_data":
            return await self._analyze_data(request.get("parameters", {}))
        else:
            return ServiceResponse(success=False, error=f"Unknown action: {action}")

    async def _process_data(self, params: Dict[str, Any]) -> ServiceResponse:
        """Process input data and store in memory."""
        try:
            data = params.get("data", "")
            context = params.get("context", "default")

            # Simulate data processing
            processed_data = f"Processed: {data}"

            # Store in memory if memory service is available
            if self.memory_service:
                entry_id = await self.memory_service.store_memory(
                    content=processed_data,
                    memory_type=MemoryType.SHORT_TERM,
                    metadata={"context": context, "processor": "data_processor"},
                    tags=["processed", "data"],
                )

                logger.info(f"Stored processed data in memory: {entry_id}")

                return ServiceResponse(
                    success=True,
                    data={
                        "processed_data": processed_data,
                        "memory_entry_id": entry_id,
                    },
                    metadata={"action": "process_data", "context": context},
                )
            else:
                return ServiceResponse(
                    success=True,
                    data={"processed_data": processed_data},
                    metadata={"action": "process_data", "context": context},
                )

        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def _analyze_data(self, params: Dict[str, Any]) -> ServiceResponse:
        """Analyze data by retrieving from memory."""
        try:
            query_text = params.get("query", "")

            if not self.memory_service:
                return ServiceResponse(
                    success=False, error="Memory service not available for analysis"
                )

            # Retrieve relevant data from memory
            result = await self.memory_service.retrieve_memory(
                content=query_text, memory_type="short_term", limit=5
            )

            # Simulate analysis
            analysis_results = []
            for entry in result.entries:
                analysis_results.append(
                    {
                        "entry_id": entry.id,
                        "content": entry.content,
                        "relevance_score": 0.8,  # Mock score
                        "metadata": entry.metadata,
                    }
                )

            # Store analysis results
            if analysis_results:
                analysis_summary = f"Analysis of {len(analysis_results)} entries for query: {query_text}"
                summary_id = await self.memory_service.store_memory(
                    content=analysis_summary,
                    memory_type=MemoryType.LONG_TERM,
                    metadata={"analysis_type": "data_analysis", "query": query_text},
                    tags=["analysis", "summary"],
                )

                logger.info(f"Stored analysis summary: {summary_id}")

            return ServiceResponse(
                success=True,
                data={
                    "analysis_results": analysis_results,
                    "total_entries": len(analysis_results),
                    "query": query_text,
                },
                metadata={"action": "analyze_data"},
            )

        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            return ServiceResponse(success=False, error=str(e))


class KnowledgeService(Service):
    """Service that manages knowledge storage and retrieval."""

    def __init__(self, name: str = "knowledge_service", config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.memory_service = None

    async def initialize(self) -> None:
        """Initialize the service."""
        logger.info("Initializing knowledge service")

    async def start(self) -> None:
        """Start the service."""
        logger.info("Starting knowledge service")

    async def stop(self) -> None:
        """Stop the service."""
        logger.info("Stopping knowledge service")

    async def health_check(self) -> ServiceResponse:
        """Check service health."""
        return ServiceResponse(success=True, data={"status": "healthy"})

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a knowledge management request."""
        action = request.get("action")

        if action == "store_knowledge":
            return await self._store_knowledge(request.get("parameters", {}))
        elif action == "search_knowledge":
            return await self._search_knowledge(request.get("parameters", {}))
        else:
            return ServiceResponse(success=False, error=f"Unknown action: {action}")

    async def _store_knowledge(self, params: Dict[str, Any]) -> ServiceResponse:
        """Store knowledge in long-term memory."""
        try:
            knowledge = params.get("knowledge", "")
            category = params.get("category", "general")

            if not self.memory_service:
                return ServiceResponse(
                    success=False, error="Memory service not available"
                )

            # Store in long-term memory for persistence
            entry_id = await self.memory_service.store_memory(
                content=knowledge,
                memory_type=MemoryType.LONG_TERM,
                metadata={"category": category, "source": "knowledge_service"},
                tags=["knowledge", category],
                priority=5,
            )

            logger.info(f"Stored knowledge in long-term memory: {entry_id}")

            return ServiceResponse(
                success=True,
                data={"entry_id": entry_id, "category": category},
                metadata={"action": "store_knowledge"},
            )

        except Exception as e:
            logger.error(f"Knowledge storage failed: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def _search_knowledge(self, params: Dict[str, Any]) -> ServiceResponse:
        """Search for knowledge using similarity search."""
        try:
            query = params.get("query", "")

            if not self.memory_service:
                return ServiceResponse(
                    success=False, error="Memory service not available"
                )

            # Use similarity search for semantic matching
            result = await self.memory_service.search_similar_memory(
                content=query,
                limit=10,
                threshold=0.3,  # Lower threshold for broader search
            )

            knowledge_items = []
            for entry in result.entries:
                knowledge_items.append(
                    {
                        "id": entry.id,
                        "content": entry.content,
                        "category": entry.metadata.get("category", "unknown"),
                        "tags": entry.tags,
                        "timestamp": entry.timestamp.isoformat(),
                    }
                )

            logger.info(
                f"Found {len(knowledge_items)} knowledge items for query: {query}"
            )

            return ServiceResponse(
                success=True,
                data={
                    "knowledge_items": knowledge_items,
                    "total_found": len(knowledge_items),
                    "query": query,
                },
                metadata={"action": "search_knowledge"},
            )

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return ServiceResponse(success=False, error=str(e))


async def main():
    """Main example function demonstrating memory service integration."""
    logger.info("Starting memory service integration example")

    # Create workflow engine
    engine = WorkflowEngine()

    # Create memory service with configuration
    memory_config = {
        "memory": {
            "short_term": {
                "max_total_entries": 100,
                "default_window_size": 20,
                "cleanup_interval": 60,
            },
            "vector_store": {
                "url": "http://localhost:8080",
                "class_name": "ExampleMemoryEntry",
            },
            "cache": {
                "use_redis": False
            },
        }
    }

    memory_service = MemoryService("memory_service", memory_config)

    # Create application services
    data_processor = DataProcessorService()
    knowledge_service = KnowledgeService()

    # Register components with engine
    engine.register_component(memory_service)
    engine.register_component(data_processor)
    engine.register_component(knowledge_service)

    try:
        # Start the engine (initializes all components)
        await engine.start()

        # Connect services to memory service
        data_processor.memory_service = memory_service
        knowledge_service.memory_service = memory_service

        logger.info("All services started successfully")

        # Demonstrate memory operations
        await demonstrate_memory_operations(
            memory_service, data_processor, knowledge_service
        )

        # Demonstrate workflow with memory
        await demonstrate_workflow_with_memory(engine, memory_service)

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
    finally:
        # Clean shutdown
        await engine.stop()
        logger.info("Example completed")


async def demonstrate_memory_operations(
    memory_service, data_processor, knowledge_service
):
    """Demonstrate various memory operations."""
    logger.info("\n=== Demonstrating Memory Operations ===")

    # 1. Direct memory operations
    logger.info("1. Direct memory storage and retrieval")

    # Store some initial data
    entry_id1 = await memory_service.store_memory(
        "Python is a programming language",
        MemoryType.SHORT_TERM,
        tags=["programming", "python"],
        metadata={"topic": "programming"},
    )

    entry_id2 = await memory_service.store_memory(
        "Machine learning uses algorithms to learn patterns",
        MemoryType.LONG_TERM,
        tags=["ml", "algorithms"],
        metadata={"topic": "machine_learning"},
    )

    logger.info(f"Stored entries: {entry_id1}, {entry_id2}")

    # Retrieve data
    result = await memory_service.retrieve_memory(content="programming", limit=5)

    logger.info(f"Retrieved {len(result.entries)} entries about programming")
    for entry in result.entries:
        logger.info(f"  - {entry.content[:50]}...")

    # 2. Service-based operations
    logger.info("\n2. Service-based data processing")

    # Process data through data processor
    response = await data_processor.process_request(
        {
            "action": "process_data",
            "parameters": {
                "data": "Raw sensor data: temperature=25.5, humidity=60%",
                "context": "sensor_processing",
            },
        }
    )

    if response.success:
        logger.info(f"Data processing result: {response.data}")

    # Analyze data
    response = await data_processor.process_request(
        {"action": "analyze_data", "parameters": {"query": "sensor"}}
    )

    if response.success:
        logger.info(f"Analysis found {response.data['total_entries']} relevant entries")

    # 3. Knowledge management
    logger.info("\n3. Knowledge management operations")

    # Store knowledge
    await knowledge_service.process_request(
        {
            "action": "store_knowledge",
            "parameters": {
                "knowledge": "Neural networks are inspired by biological neural networks",
                "category": "artificial_intelligence",
            },
        }
    )

    await knowledge_service.process_request(
        {
            "action": "store_knowledge",
            "parameters": {
                "knowledge": "Deep learning is a subset of machine learning",
                "category": "artificial_intelligence",
            },
        }
    )

    # Search knowledge
    response = await knowledge_service.process_request(
        {
            "action": "search_knowledge",
            "parameters": {"query": "neural networks and learning"},
        }
    )

    if response.success:
        logger.info(f"Knowledge search found {response.data['total_found']} items")
        for item in response.data["knowledge_items"]:
            logger.info(f"  - {item['content'][:50]}... (category: {item['category']})")

    # 4. Memory statistics
    logger.info("\n4. Memory statistics")

    stats_response = await memory_service.process_request(
        {"action": "get_stats", "parameters": {}}
    )

    if stats_response.success:
        stats = stats_response.data
        logger.info(f"Total operations: {stats['total_operations']}")
        logger.info(f"Store operations: {stats['operations_by_type']}")

        for store_name, store_stats in stats["stores"].items():
            logger.info(f"{store_name}: {store_stats['total_entries']} entries")


async def demonstrate_workflow_with_memory(engine, memory_service):
    """Demonstrate workflow execution with memory integration."""
    logger.info("\n=== Demonstrating Workflow with Memory ===")

    # Create a workflow that uses memory
    workflow = WorkflowDefinition(
        id="memory_workflow",
        name="Memory Integration Workflow",
        description="Workflow demonstrating memory service integration",
        steps=[
            WorkflowStep(
                id="store_input",
                name="Store Input Data",
                component="memory_service",
                action="store",
                parameters={
                    "content": "Workflow input: User query about AI systems",
                    "memory_type": "short_term",
                    "tags": ["workflow", "input"],
                    "metadata": {"step": "input", "workflow_id": "memory_workflow"},
                },
            ),
            WorkflowStep(
                id="process_data",
                name="Process Data",
                component="data_processor",
                action="process_data",
                parameters={
                    "data": "AI systems require careful design and testing",
                    "context": "workflow_processing",
                },
                dependencies=["store_input"],
            ),
            WorkflowStep(
                id="search_knowledge",
                name="Search Knowledge",
                component="knowledge_service",
                action="search_knowledge",
                parameters={"query": "AI systems design"},
                dependencies=["process_data"],
            ),
            WorkflowStep(
                id="store_result",
                name="Store Final Result",
                component="memory_service",
                action="store",
                parameters={
                    "content": "Workflow completed: AI systems analysis finished",
                    "memory_type": "long_term",
                    "tags": ["workflow", "result", "ai"],
                    "metadata": {"step": "output", "workflow_id": "memory_workflow"},
                },
                dependencies=["search_knowledge"],
            ),
        ],
    )

    # Execute workflow
    logger.info("Executing memory integration workflow...")

    try:
        execution = await engine.execute_workflow(workflow)

        if execution.status == "completed":
            logger.info("Workflow completed successfully!")
            logger.info(f"Completed steps: {execution.completed_steps}")

            # Show final memory state
            final_stats = await memory_service.process_request(
                {"action": "get_stats", "parameters": {}}
            )

            if final_stats.success:
                logger.info(
                    f"Final memory state: {final_stats.data['total_operations']} total operations"
                )
        else:
            logger.error(f"Workflow failed: {execution.error}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
