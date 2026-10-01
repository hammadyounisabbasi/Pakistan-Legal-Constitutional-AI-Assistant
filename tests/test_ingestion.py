from datetime import UTC, datetime

from backend.app.ingestion.chunker import legal_chunks
from backend.app.models.legal_document import LegalDocument
from backend.app.services.catalog import Catalog


def test_legal_chunking_preserves_provision_metadata():
    text = "Article 25 Equality of citizens\n" + ("All citizens are equal before law. " * 100)
    chunks = legal_chunks(text, target_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(chunk.metadata["article"] == "25" for chunk in chunks)


def test_numbered_statutory_heading_becomes_section():
    chunks = legal_chunks("302. Punishment for murder\n" + ("Whoever commits murder shall be punished. " * 20), target_chars=500)
    assert chunks[0].metadata["section"] == "302"


def test_catalog_detects_unchanged_document(tmp_path):
    catalog = Catalog(tmp_path / "catalog.db")
    doc = LegalDocument(
        id="constitution", title="Constitution", source_name="National Assembly",
        source_url="https://na.gov.pk/test.pdf", document_type="constitution", content_hash="abc",
    )
    catalog.upsert(doc, 2, datetime.now(UTC).isoformat())
    assert catalog.unchanged(doc.source_url, "abc") is True
    assert catalog.unchanged(doc.source_url, "different") is False
    assert catalog.count() == 1
