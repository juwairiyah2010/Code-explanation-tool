"""Embedding services for RAG: local fastembed and remote LLM providers."""

import math
from abc import ABC, abstractmethod
import httpx
from backend.config import get_settings
from backend.core.logging import logger


class BaseEmbeddingService(ABC):
    """Abstract base class for vector embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality."""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a batch of text strings."""
        pass

    def embed_text(self, text: str) -> list[float]:
        """Compute embedding for a single text string."""
        results = self.embed_texts([text])
        if not results:
            raise ValueError("Embedding returned empty result.")
        return results[0]


class FastEmbedService(BaseEmbeddingService):
    """Local dense embedding model using FastEmbed with ONNX runtime (zero external API dependency)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = None
        self._dim = 384

    @property
    def dimension(self) -> int:
        return self._dim

    def _get_model(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(self.model_name)
            except Exception as e:
                logger.error(f"Failed to initialize FastEmbed model '{self.model_name}': {e}")
                raise RuntimeError(f"FastEmbed initialization error: {e}") from e
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        # FastEmbed returns an iterator of numpy ndarrays
        embeddings = list(model.embed(texts))
        return [vec.tolist() for vec in embeddings]


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI remote embedding service."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": self.model}
        with httpx.Client(timeout=20.0) as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            return [item["embedding"] for item in data["data"]]


class MockEmbeddingService(BaseEmbeddingService):
    """Deterministic hash-based embedding service for unit testing and offline mock scenarios."""

    def __init__(self, dimension: int = 64):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            # Deterministic projection from text tokens to unit sphere
            words = text.lower().split()
            vec = [0.0] * self._dim
            for i, word in enumerate(words):
                h = hash(word)
                idx = abs(h) % self._dim
                vec[idx] += 1.0 / (1.0 + (i * 0.1))

            # Normalize to unit length
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            results.append([x / norm for x in vec])
        return results


def get_embedding_service(override_provider: str | None = None) -> BaseEmbeddingService:
    """Factory returning configured embedding service."""
    settings = get_settings()
    provider = override_provider or getattr(settings, "EMBEDDING_PROVIDER", "fastembed")

    if provider == "openai" and getattr(settings, "OPENAI_API_KEY", ""):
        return OpenAIEmbeddingService(api_key=settings.OPENAI_API_KEY)
    elif provider == "mock":
        return MockEmbeddingService()

    # Default to fastembed (local, fast, reliable, zero external tokens)
    try:
        return FastEmbedService()
    except Exception as e:
        logger.warning(f"FastEmbed unavailable, falling back to deterministic mock embeddings: {e}")
        return MockEmbeddingService()
