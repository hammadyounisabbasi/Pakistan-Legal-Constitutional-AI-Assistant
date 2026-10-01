import httpx

from backend.app.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, endpoint: str, api_key: str, model: str, timeout: float):
        self.name, self.endpoint, self.api_key, self.model = name, endpoint, api_key, model
        self.timeout = timeout

    async def generate(self, system: str, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": 1400,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    async def generate(self, system: str, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1400},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


class HuggingFaceProvider(LLMProvider):
    name = "huggingface"

    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    async def generate(self, system: str, prompt: str) -> str:
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        payload = {"inputs": f"{system}\n\n{prompt}", "parameters": {"max_new_tokens": 700, "temperature": 0.1}}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
            response.raise_for_status()
            data = response.json()
            return data[0]["generated_text"].removeprefix(payload["inputs"]).strip()


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float):
        self.base_url, self.model, self.timeout = base_url.rstrip("/"), model, timeout

    async def generate(self, system: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1400},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()["response"].strip()
