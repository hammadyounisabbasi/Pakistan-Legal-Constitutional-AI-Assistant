from backend.app.vectorstore.base import SearchResult, VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_directory: str, collection_name: str, embeddings):
        from langchain_chroma import Chroma

        self.store = Chroma(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add(self, texts: list[str], metadatas: list[dict], ids: list[str]) -> None:
        self.store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def delete_document(self, document_id: str) -> None:
        self.store._collection.delete(where={"document_id": document_id})

    def search(self, query: str, limit: int = 8, where: dict | None = None) -> list[SearchResult]:
        pairs = self.store.similarity_search_with_relevance_scores(query, k=limit, filter=where)
        return [SearchResult(doc.page_content, doc.metadata, float(score)) for doc, score in pairs]

    def count(self) -> int:
        return self.store._collection.count()

