from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class LLMResult:
    text: str
    provider: str


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, system: str, prompt: str) -> str: ...

