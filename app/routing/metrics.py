from app.storage.memory import MemoryStore
from app.routing.circuit_breaker import CircuitBreaker


class MetricsService:
    def __init__(self):
        self.memory = MemoryStore()
        self.circuit_breaker = CircuitBreaker()

    async def record(self, provider_name: str, latency_ms: int, cost: float, success: bool):
        await self.memory.record_request_metrics(provider_name, latency_ms, cost, success)

    async def get_global_metrics(self) -> dict:
        return await self.memory.get_global_metrics()

    async def get_provider_metrics(self) -> dict[str, dict]:
        provider_metrics = await self.memory.get_provider_metrics()
        
        for provider_name in provider_metrics.keys():
            state = await self.memory.get_provider_dynamic_state(provider_name)
            provider_metrics[provider_name]["is_down"] = state["is_down"]
            provider_metrics[provider_name]["circuit_status"] = await self.circuit_breaker.get_status(provider_name)
        
        return provider_metrics
