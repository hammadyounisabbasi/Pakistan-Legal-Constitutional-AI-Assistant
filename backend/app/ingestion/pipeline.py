import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.core.logging import get_logger
from backend.app.ingestion.chunker import legal_chunks
from backend.app.ingestion.downloader import SafeDownloader
from backend.app.ingestion.extractor import extract_text
from backend.app.models.legal_document import LegalDocument
from backend.app.services.catalog import Catalog

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, settings: Settings, catalog: Catalog, vector_store):
        self.settings, self.catalog, self.vector_store = settings, catalog, vector_store
        self.downloader = SafeDownloader(
            settings.ingest_user_agent, settings.ingest_timeout_seconds,
            settings.ingest_max_bytes, settings.ingest_request_delay_seconds,
        )

    async def run(self, source_config: Path, force: bool = False) -> dict:
        sources = json.loads(source_config.read_text(encoding="utf-8"))
        report = {"discovered": len(sources), "indexed": 0, "unchanged": 0, "failed": []}
        for source in sources:
            if not source.get("enabled", True):
                continue
            try:
                downloaded = await self.downloader.fetch(source["source_url"])
                digest = hashlib.sha256(downloaded.content).hexdigest()
                if not force and self.catalog.unchanged(source["source_url"], digest):
                    report["unchanged"] += 1
                    continue
                text = extract_text(downloaded.content, downloaded.content_type, downloaded.final_url)
                if len(text) < 200:
                    raise ValueError("Extracted content is unexpectedly short")
                doc = LegalDocument(
                    id=source["id"], title=source["title"], source_name=source["source_name"],
                    source_url=source["source_url"], document_type=source["document_type"],
                    issuing_authority=source.get("issuing_authority"),
                    publication_date=source.get("publication_date"), version=source.get("version"),
                    effective_status=source.get("effective_status"), content_hash=digest, text=text,
                    metadata={k: v for k, v in source.items() if k not in {"enabled"}},
                )
                chunks = legal_chunks(text)
                base = {
                    "document_id": doc.id, "title": doc.title, "source_name": doc.source_name,
                    "source_url": doc.source_url, "document_type": doc.document_type,
                    "jurisdiction": doc.jurisdiction, "effective_status": doc.effective_status or "unknown",
                    "content_hash": digest,
                }
                metadatas = [{**base, **chunk.metadata, "chunk_index": i} for i, chunk in enumerate(chunks)]
                ids = [f"{doc.id}:{digest[:12]}:{i}" for i in range(len(chunks))]
                self.vector_store.delete_document(doc.id)
                self.vector_store.add([chunk.text for chunk in chunks], metadatas, ids)
                self.catalog.upsert(doc, len(chunks), datetime.now(UTC).isoformat())
                report["indexed"] += 1
                logger.info("document_indexed", document_id=doc.id, chunks=len(chunks))
            except Exception as exc:
                failure = {"source_url": source.get("source_url"), "error": type(exc).__name__, "message": str(exc)}
                report["failed"].append(failure)
                logger.error("document_failed", **failure)
        if report["failed"]:
            failed_path = self.settings.data_dir / "failed_documents.jsonl"
            with failed_path.open("a", encoding="utf-8") as handle:
                for failure in report["failed"]:
                    handle.write(json.dumps({**failure, "at": datetime.now(UTC).isoformat()}) + "\n")
        return report
