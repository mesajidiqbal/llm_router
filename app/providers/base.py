from abc import ABC, abstractmethod
from app.models import ChatResponse


class RateLimitError(Exception):
    pass


class ProviderClient(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def chat(self, prompt: str, timeout_ms: int) -> ChatResponse:
        pass
