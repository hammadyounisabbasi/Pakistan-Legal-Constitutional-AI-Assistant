from datetime import datetime

from pydantic import BaseModel


class SourceSummary(BaseModel):
    id: str
    title: str
    source_name: str
    source_url: str
    document_type: str
    jurisdiction: str
    version: str | None
    effective_status: str | None
    retrieval_date: datetime


class SourceDetail(SourceSummary):
    issuing_authority: str | None
    publication_date: str | None
    content_hash: str
    metadata: dict

