import asyncio
import random
import time
from typing import Dict
from app.providers.base import ProviderClient, RateLimitError
from app.models import ChatResponse
from app.config import ProviderRegistry, ProviderSpec
from app.routing.strategy import estimate_cost
from app.storage.memory import MemoryStore





class MockProvider(ProviderClient):
    def __init__(self, spec: ProviderSpec):
        super().__init__(spec.name)
        self.spec = spec
        self.memory = MemoryStore()

    async def chat(self, prompt: str, timeout_ms: int) -> ChatResponse:
        start_time = time.time()
        
        await self.memory.check_and_increment_rate_limit(self.name, self.spec.rate_limit_rpm)
        
        await asyncio.sleep(self.spec.latency_ms / 1000)
        
        if random.random() < 0.1:
            raise Exception(f"Random failure from {self.name}")
        
        actual_latency_ms = int((time.time() - start_time) * 1000)
        cost = estimate_cost(self.spec, prompt)
        
        return ChatResponse(
            provider_used=self.name,
            content=f"Mock response from {self.name}: {prompt[:50]}...",
            latency_ms=actual_latency_ms,
            cost=cost,
        )


_provider_cache: Dict[str, MockProvider] = {}


def get_provider(name: str) -> MockProvider:
    if name not in _provider_cache:
        providers_dict = ProviderRegistry.providers_dict()
        if name not in providers_dict:
            raise ValueError(f"Unknown provider: {name}")
        _provider_cache[name] = MockProvider(providers_dict[name])
    return _provider_cache[name]


def list_providers() -> list[MockProvider]:
    providers_list = ProviderRegistry.providers_list()
    return [get_provider(spec.name) for spec in providers_list]
