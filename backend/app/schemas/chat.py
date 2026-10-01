from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=100)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class SourceCitation(BaseModel):
    id: str
    title: str
    source_name: str
    source_url: HttpUrl
    document_type: str
    provision: str | None = None
    effective_status: str | None = None
    excerpt: str | None = None


class ChatResponse(BaseModel):
    answer: str
    scope: Literal["pakistan_law", "out_of_scope", "unclear"]
    grounding: Literal["rag", "partial_rag", "unverified_llm", "none"]
    sources: list[SourceCitation] = Field(default_factory=list)
    language: Literal["english", "urdu", "roman_urdu", "mixed"]
    request_id: str
    disclaimer: str

