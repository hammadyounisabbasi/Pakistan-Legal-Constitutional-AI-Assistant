from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pakistan Legal & Constitutional AI Assistant"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    app_rate_limit_per_minute: int = 30
    app_max_query_chars: int = 4000
    app_developer_name: str = "Hammad Younis Abbasi"
    app_contact_url: str = ""

    data_dir: Path = Path("./data")
    database_url: str = "sqlite:///./data/catalog.db"
    vector_provider: str = "chroma"
    chroma_collection: str = "pakistan_legal_documents_v2"
    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_fallback_provider: str = "hashing"
    hashing_embedding_dimensions: int = 768

    llm_provider_chain: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["groq", "gemini", "huggingface", "ollama"]
    )
    llm_timeout_seconds: float = 30
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    huggingface_api_key: str = ""
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    ingest_user_agent: str = "PakistanLegalAssistant/1.0"
    ingest_request_delay_seconds: float = 1.5
    ingest_timeout_seconds: float = 30
    ingest_max_bytes: int = 52_428_800

    @field_validator("app_allowed_origins", "llm_provider_chain", mode="before")
    @classmethod
    def parse_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def vector_path(self) -> Path:
        return self.data_dir / "vectorstore"

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        return Path(self.database_url.removeprefix(prefix))

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.vector_path.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
