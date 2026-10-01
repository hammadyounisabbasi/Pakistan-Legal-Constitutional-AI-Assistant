from backend.app.core.config import Settings


def test_csv_environment_settings(monkeypatch):
    monkeypatch.setenv("APP_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "groq,gemini,ollama")
    settings = Settings(_env_file=None)
    assert settings.app_allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert settings.llm_provider_chain == ["groq", "gemini", "ollama"]
