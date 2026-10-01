import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.app.models.legal_document import LegalDocument

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, source_name TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE, document_type TEXT NOT NULL,
  jurisdiction TEXT NOT NULL, issuing_authority TEXT, publication_date TEXT,
  retrieval_date TEXT NOT NULL, version TEXT, effective_status TEXT,
  content_hash TEXT NOT NULL, metadata_json TEXT NOT NULL,
  indexed_at TEXT, chunk_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
"""


class Catalog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def unchanged(self, source_url: str, content_hash: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT content_hash FROM documents WHERE source_url = ?", (source_url,)
            ).fetchone()
        return bool(row and row["content_hash"] == content_hash)

    def upsert(self, doc: LegalDocument, chunk_count: int, indexed_at: str) -> None:
        values = (
            doc.id, doc.title, doc.source_name, doc.source_url, doc.document_type,
            doc.jurisdiction, doc.issuing_authority, doc.publication_date,
            doc.retrieval_date, doc.version, doc.effective_status, doc.content_hash,
            json.dumps(doc.metadata, ensure_ascii=False), indexed_at, chunk_count,
        )
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_url) DO UPDATE SET
                id=excluded.id,title=excluded.title,source_name=excluded.source_name,
                document_type=excluded.document_type,jurisdiction=excluded.jurisdiction,
                issuing_authority=excluded.issuing_authority,
                publication_date=excluded.publication_date,retrieval_date=excluded.retrieval_date,
                version=excluded.version,effective_status=excluded.effective_status,
                content_hash=excluded.content_hash,metadata_json=excluded.metadata_json,
                indexed_at=excluded.indexed_at,chunk_count=excluded.chunk_count""",
                values,
            )

    def list(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY retrieval_date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row(row) for row in rows]

    def get(self, document_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._row(row) if row else None

    def count(self) -> int:
        with self.connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json"))
        return result

