"""Embedding services for RAG: local fastembed and remote LLM providers with LRU caching."""

from abc import ABC, abstractmethod
from collections import OrderedDict
import hashlib
import math
import threading
import httpx

from backend.config import get_settings
from backend.core.logging import logger


class EmbeddingCache:
    """Thread-safe LRU cache for computed vector embeddings."""

    def __init__(self, maxsize: int = 4096):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, text: str) -> list[float] | None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, text: str, embedding: list[float]) -> None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
                self._cache[key] = embedding

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class BaseEmbeddingService(ABC):
    """Abstract base class for vector embedding generation with integrated LRU caching."""

    def __init__(self, cache_size: int = 4096):
        self.cache = EmbeddingCache(maxsize=cache_size)

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality."""
        pass

    @abstractmethod
    def _compute_embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a batch of text strings (uncached)."""
        pass

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings with LRU cache lookup and batch computation for misses."""
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for idx, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                results[idx] = cached
            else:
                missing_indices.append(idx)
                missing_texts.append(text)

        if missing_texts:
            computed_vectors = self._compute_embed_texts(missing_texts)
            for orig_idx, text, vec in zip(missing_indices, missing_texts, computed_vectors):
                self.cache.put(text, vec)
                results[orig_idx] = vec

        return [r for r in results if r is not None]

    def embed_text(self, text: str) -> list[float]:
        """Compute embedding for a single text string with cache support."""
        cached = self.cache.get(text)
        if cached is not None:
            return cached

        results = self._compute_embed_texts([text])
        if not results:
            raise ValueError("Embedding returned empty result.")
        vec = results[0]
        self.cache.put(text, vec)
        return vec


class FastEmbedService(BaseEmbeddingService):
    """Local dense embedding model using FastEmbed with ONNX runtime (zero external API dependency)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", cache_size: int = 4096):
        super().__init__(cache_size=cache_size)
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

    def _compute_embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        # FastEmbed returns an iterator of numpy ndarrays
        embeddings = list(model.embed(texts))
        return [vec.tolist() for vec in embeddings]


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI remote embedding service."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", cache_size: int = 4096):
        super().__init__(cache_size=cache_size)
        self.api_key = api_key
        self.model = model
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    def _compute_embed_texts(self, texts: list[str]) -> list[list[float]]:
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

    def __init__(self, dimension: int = 64, cache_size: int = 4096):
        super().__init__(cache_size=cache_size)
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _compute_embed_texts(self, texts: list[str]) -> list[list[float]]:
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


# Module-level singletons to prevent repeated model initializations and share cache
_singleton_lock = threading.Lock()
_embedding_service_instance: BaseEmbeddingService | None = None
_embedding_provider_cached: str | None = None


def get_embedding_service(override_provider: str | None = None) -> BaseEmbeddingService:
    """Factory returning configured embedding service with singleton caching."""
    global _embedding_service_instance, _embedding_provider_cached

    settings = get_settings()
    provider = override_provider or getattr(settings, "EMBEDDING_PROVIDER", "fastembed")

    with _singleton_lock:
        if _embedding_service_instance is not None and _embedding_provider_cached == provider:
            return _embedding_service_instance

        if provider == "openai" and getattr(settings, "OPENAI_API_KEY", ""):
            svc = OpenAIEmbeddingService(api_key=settings.OPENAI_API_KEY)
        elif provider == "mock":
            svc = MockEmbeddingService()
        else:
            try:
                svc = FastEmbedService()
            except Exception as e:
                logger.warning(f"FastEmbed unavailable, falling back to deterministic mock embeddings: {e}")
                svc = MockEmbeddingService()

        _embedding_service_instance = svc
        _embedding_provider_cached = provider
        return svc
