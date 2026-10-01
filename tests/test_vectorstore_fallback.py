import pytest

from backend.app.vectorstore.base import UnavailableVectorStore


def test_unavailable_vector_store_is_safe_for_chat_but_rejects_ingestion():
    store = UnavailableVectorStore("dependencies missing")
    assert store.search("Article 25") == []
    assert store.count() == 0
    with pytest.raises(RuntimeError, match="dependencies missing"):
        store.add(["text"], [{}], ["id"])
