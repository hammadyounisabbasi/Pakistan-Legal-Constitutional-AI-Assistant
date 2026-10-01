from functools import lru_cache

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.embeddings.factory import get_embeddings
from backend.app.vectorstore.base import UnavailableVectorStore
from backend.app.vectorstore.chroma import ChromaVectorStore

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_vector_store():
    settings = get_settings()
    if settings.vector_provider == "chroma":
        try:
            return ChromaVectorStore(
                str(settings.vector_path), settings.chroma_collection, get_embeddings()
            )
        except (ImportError, ModuleNotFoundError) as exc:
            logger.warning(
                "vector_dependencies_unavailable",
                dependency=getattr(exc, "name", type(exc).__name__),
            )
            return UnavailableVectorStore(
                "Install requirements.txt to enable Chroma and multilingual embeddings"
            )
    raise ValueError(f"Unsupported vector provider: {settings.vector_provider}")
