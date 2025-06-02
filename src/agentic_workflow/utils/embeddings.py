"""Vector embedding utilities."""

import random
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings

from ..core.config import get_config
from ..core.logging_config import get_logger
from .base import BaseEmbeddingProvider

logger = get_logger(__name__)


class EmbeddingProvider(BaseEmbeddingProvider):
    """Provider for text embeddings."""

    def __init__(self, model_name: str = "text-embedding-ada-002"):
        """Initialize embedding provider."""
        self.model_name = model_name
        self._client: Optional[OpenAIEmbeddings] = None

    async def embed_text(self, text: str) -> List[float]:
        """Get embedding for text."""
        if not self._client:
            self._client = OpenAIEmbeddings(model=self.model_name)
        result = await self._client.aembed_query(text)
        return result

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for batch of texts."""
        if not self._client:
            self._client = OpenAIEmbeddings(model=self.model_name)
        results = await self._client.aembed_documents(texts)
        return results


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-based embedding provider using LangChain."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI embedding provider.

        Args:
            config: Configuration parameters
        """
        config = config or {}
        super().__init__(config.get("model", "text-embedding-ada-002"))

        # Get configuration
        app_config = get_config()
        api_key = config.get("api_key", app_config.llm.openai_api_key)

        # Initialize embeddings
        try:
            self._client = OpenAIEmbeddings(api_key=api_key, model=self.model_name)
            logger.info(f"Initialized OpenAI embeddings with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            self._client = None

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Vector embedding
        """
        if not self._client:
            logger.warning("OpenAI embeddings not available")
            return self._generate_random_embedding()

        try:
            # Use LangChain to get embedding
            embedding = await self._client.aembed_query(text)
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
        if not self._client:
            logger.warning("OpenAI embeddings not available")
            return [self._generate_random_embedding() for _ in texts]

        try:
            # Use LangChain to get embeddings
            embeddings = await self._client.aembed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embeddings in batch: {e}")
            return [self._generate_random_embedding() for _ in texts]

    def _generate_random_embedding(self) -> List[float]:
        """Generate a random embedding for fallback.

        Returns:
            Random vector embedding
        """
        return [random.uniform(-1, 1) for _ in range(1536)]


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize mock embedding provider.

        Args:
            config: Configuration parameters
        """
        config = config or {}
        super().__init__(config.get("model", "text-embedding-ada-002"))

    async def embed_text(self, text: str) -> List[float]:
        """Generate mock embedding for text.

        Args:
            text: Text to embed

        Returns:
            Random vector embedding
        """
        return [random.uniform(-1, 1) for _ in range(1536)]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of random vector embeddings
        """
        return [[random.uniform(-1, 1) for _ in range(1536)] for _ in texts]


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
    if provider_type == "openai":
        return OpenAIEmbeddingProvider(config)
    elif provider_type == "mock":
        return MockEmbeddingProvider(config)
    else:
        raise ValueError(f"Unknown embedding provider type: {provider_type}")
