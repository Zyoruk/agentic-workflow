"""Vector embedding utilities."""

import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..core.config import get_config
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Check if LangChain OpenAI embeddings are available
try:
    from langchain_openai import OpenAIEmbeddings

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    OpenAIEmbeddings = None  # type: ignore


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize embedding provider.

        Args:
            config: Configuration parameters
        """
        self.config = config or {}
        self.dimension: int = 1536  # Default for OpenAI embeddings

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Vector embedding
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector embeddings
        """
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-based embedding provider using LangChain."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI embedding provider.

        Args:
            config: Configuration parameters
        """
        super().__init__(config)

        if not LANGCHAIN_AVAILABLE:
            logger.warning(
                "LangChain OpenAI embeddings not available - install optional dependency: "
                "pip install agentic-workflow[embedding]"
            )
            self.embeddings = None
            return

        # Get configuration
        app_config = get_config()
        api_key = self.config.get("api_key", app_config.llm.openai_api_key)
        model = self.config.get("model", "text-embedding-3-small")

        # Initialize embeddings
        try:
            self.embeddings = OpenAIEmbeddings(api_key=api_key, model=model)
            # Set dimension based on model
            if model == "text-embedding-3-small":
                self.dimension = 1536
            elif model == "text-embedding-3-large":
                self.dimension = 3072
            elif model == "text-embedding-ada-002":
                self.dimension = 1536

            logger.info(f"Initialized OpenAI embeddings with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            self.embeddings = None

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Vector embedding
        """
        if not self.embeddings:
            logger.warning("OpenAI embeddings not available")
            return self._generate_random_embedding()

        try:
            # Use LangChain to get embedding
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embedding: {e}")
            return self._generate_random_embedding()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using OpenAI.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector embeddings
        """
        if not self.embeddings:
            logger.warning("OpenAI embeddings not available")
            return [self._generate_random_embedding() for _ in texts]

        try:
            # Use LangChain to get embeddings
            embeddings = await self.embeddings.aembed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embeddings in batch: {e}")
            return [self._generate_random_embedding() for _ in texts]

    def _generate_random_embedding(self) -> List[float]:
        """Generate a random embedding for fallback.

        Returns:
            Random vector embedding
        """
        return [random.uniform(-1, 1) for _ in range(self.dimension)]


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize mock embedding provider.

        Args:
            config: Configuration parameters
        """
        super().__init__(config)
        self.dimension = self.config.get("dimension", 1536)

    async def embed_text(self, text: str) -> List[float]:
        """Generate mock embedding for text.

        Args:
            text: Text to embed

        Returns:
            Random vector embedding
        """
        return [random.uniform(-1, 1) for _ in range(self.dimension)]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of random vector embeddings
        """
        return [[random.uniform(-1, 1) for _ in range(self.dimension)] for _ in texts]


def get_embedding_provider(
    provider_type: str = "openai", config: Optional[Dict[str, Any]] = None
) -> EmbeddingProvider:
    """Get embedding provider instance.

    Args:
        provider_type: Type of embedding provider ("openai" or "mock")
        config: Configuration parameters

    Returns:
        Embedding provider instance
    """
    if provider_type == "openai" and LANGCHAIN_AVAILABLE:
        return OpenAIEmbeddingProvider(config)
    else:
        if provider_type == "openai" and not LANGCHAIN_AVAILABLE:
            logger.warning(
                "LangChain OpenAI embeddings not available, falling back to mock provider"
            )
        return MockEmbeddingProvider(config)
