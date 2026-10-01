from functools import lru_cache

from backend.app.core.config import get_settings
from backend.app.llm.factory import build_provider_chain
from backend.app.rag.service import RAGService
from backend.app.services.catalog import Catalog
from backend.app.vectorstore.factory import get_vector_store


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    settings = get_settings()
    return Catalog(settings.database_path)


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    settings = get_settings()
    return RAGService(settings, get_vector_store(), build_provider_chain(settings))

