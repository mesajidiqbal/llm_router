import asyncio
import importlib
import random
import time
from typing import Dict, Type

from app.config import ProviderRegistry, ProviderSpec, settings
from app.models import ChatResponse
from app.providers.base import ProviderClient
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

        if random.random() < settings.mock_failure_rate:
            raise Exception(f"Random failure from {self.name}")

        actual_latency_ms = int((time.time() - start_time) * 1000)
        cost = estimate_cost(self.spec, prompt)

        return ChatResponse(
            provider_used=self.name,
            content=f"Mock response from {self.name}: {prompt[:50]}...",
            latency_ms=actual_latency_ms,
            cost=cost,
        )


_provider_cache: Dict[str, ProviderClient] = {}


def import_class(class_path: str) -> Type[ProviderClient]:
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_provider(name: str) -> ProviderClient:
    """
    Factory function to get a provider instance by name.
    Manages caching and instantiation of provider clients.
    """
    if name not in _provider_cache:
        providers_dict = ProviderRegistry.providers_dict()
        if name not in providers_dict:
            raise ValueError(f"Unknown provider: {name}")

        spec = providers_dict[name]

        # Check if mock mode is enabled
        if settings.mock:
            _provider_cache[name] = MockProvider(spec)
            return _provider_cache[name]

        if not spec.provider_class:
            raise ValueError(f"Provider class not defined for {name}")

        try:
            provider_class = import_class(spec.provider_class)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import provider class {spec.provider_class}: {e}")

        # Dynamic API key lookup
        api_key = None
        if spec.api_key_var:
            api_key_val = getattr(settings, spec.api_key_var, None)
            if api_key_val and hasattr(api_key_val, "get_secret_value"):
                api_key = api_key_val.get_secret_value()
            else:
                api_key = api_key_val

        if not api_key:
            raise ValueError(f"{spec.api_key_var or 'API key'} not found for provider {name}")

        _provider_cache[name] = provider_class(spec, api_key)

    return _provider_cache[name]


def list_providers() -> list[ProviderClient]:
    providers_list = ProviderRegistry.providers_list()
    return [get_provider(spec.name) for spec in providers_list]
