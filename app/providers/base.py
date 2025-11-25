from abc import ABC, abstractmethod

from app.models import ChatResponse


class ProviderClient(ABC):
    """
    Abstract base class for all LLM providers.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def chat(self, prompt: str, timeout_ms: int) -> ChatResponse:
        pass
