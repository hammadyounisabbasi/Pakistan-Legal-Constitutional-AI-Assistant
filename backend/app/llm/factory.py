from backend.app.core.config import Settings
from backend.app.core.logging import get_logger
from backend.app.llm.base import LLMResult
from backend.app.llm.providers import (
    GeminiProvider,
    HuggingFaceProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
)

logger = get_logger(__name__)


class ProviderChain:
    def __init__(self, providers):
        self.providers = providers

    async def generate(self, system: str, prompt: str) -> LLMResult | None:
        for provider in self.providers:
            try:
                text = await provider.generate(system, prompt)
                if text:
                    return LLMResult(text=text, provider=provider.name)
            except Exception as exc:
                logger.warning("llm_provider_failed", provider=provider.name, error=type(exc).__name__)
        return None


def build_provider_chain(settings: Settings) -> ProviderChain:
    providers = []
    for name in settings.llm_provider_chain:
        if name == "groq" and settings.groq_api_key:
            providers.append(OpenAICompatibleProvider(
                "groq", "https://api.groq.com/openai/v1/chat/completions",
                settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds,
            ))
        elif name == "gemini" and settings.gemini_api_key:
            providers.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds))
        elif name == "huggingface" and settings.huggingface_api_key:
            providers.append(HuggingFaceProvider(settings.huggingface_api_key, settings.huggingface_model, settings.llm_timeout_seconds))
        elif name == "ollama":
            providers.append(OllamaProvider(settings.ollama_base_url, settings.ollama_model, min(settings.llm_timeout_seconds, 8)))
    return ProviderChain(providers)
