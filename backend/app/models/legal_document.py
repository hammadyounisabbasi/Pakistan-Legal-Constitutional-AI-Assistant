from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class LegalDocument:
    id: str
    title: str
    source_name: str
    source_url: str
    document_type: str
    jurisdiction: str = "Pakistan"
    issuing_authority: str | None = None
    publication_date: str | None = None
    retrieval_date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    version: str | None = None
    effective_status: str | None = None
    content_hash: str = ""
    text: str = ""
    metadata: dict = field(default_factory=dict)

