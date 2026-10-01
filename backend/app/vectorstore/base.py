from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class SearchResult:
    text: str
    metadata: dict
    relevance: float


class VectorStore(ABC):
    @abstractmethod
    def add(self, texts: list[str], metadatas: list[dict], ids: list[str]) -> None: ...

    @abstractmethod
    def delete_document(self, document_id: str) -> None: ...

    @abstractmethod
    def search(self, query: str, limit: int = 8, where: dict | None = None) -> list[SearchResult]: ...

    @abstractmethod
    def count(self) -> int: ...


class UnavailableVectorStore(VectorStore):
    """Read-safe fallback used when optional vector dependencies are not installed."""

    def __init__(self, reason: str):
        self.reason = reason

    def add(self, texts: list[str], metadatas: list[dict], ids: list[str]) -> None:
        raise RuntimeError(f"Vector store is unavailable: {self.reason}")

    def delete_document(self, document_id: str) -> None:
        raise RuntimeError(f"Vector store is unavailable: {self.reason}")

    def search(self, query: str, limit: int = 8, where: dict | None = None) -> list[SearchResult]:
        return []

    def count(self) -> int:
        return 0
