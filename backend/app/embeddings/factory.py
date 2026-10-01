import hashlib
import math
import re
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class HashingEmbeddings(Embeddings):
    """Dependency-free lexical/character embeddings for constrained machines.

    This fallback is deterministic and multilingual at the character level. It is
    less semantically capable than a transformer model, but keeps ingestion and
    retrieval functional when native ML libraries are blocked by OS policy.
    """

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        normalized = re.sub(r"\s+", " ", text.casefold()).strip()
        words = re.findall(r"\w+", normalized, flags=re.UNICODE)
        compact = re.sub(r"\s+", "_", normalized)
        features = words + [compact[i:i + 3] for i in range(max(0, len(compact) - 2))]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            index = value % self.dimensions
            vector[index] += -1.0 if value & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@lru_cache(maxsize=1)
def get_embeddings():
    settings = get_settings()
    if settings.embedding_provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except (ImportError, OSError) as exc:
            if settings.embedding_fallback_provider != "hashing":
                raise
            logger.warning(
                "embedding_provider_fallback",
                primary="huggingface",
                fallback="hashing",
                error=type(exc).__name__,
            )
            return HashingEmbeddings(settings.hashing_embedding_dimensions)
    if settings.embedding_provider == "hashing":
        return HashingEmbeddings(settings.hashing_embedding_dimensions)
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
