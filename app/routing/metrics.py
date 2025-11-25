"""
Metrics collection and aggregation service.

This module provides functionality for tracking request metrics across all
providers, including latency, cost, success rates, and circuit breaker status.
"""

from app.routing.circuit_breaker import CircuitBreaker
from app.storage.memory import MemoryStore


class MetricsService:
    """
    Service for recording and retrieving request metrics.

    This service acts as an interface to the memory store for metrics
    collection and aggregation, combining metrics data with circuit
    breaker status for comprehensive provider health monitoring.

    Attributes:
        memory: The memory store for persisting metrics data
        circuit_breaker: Circuit breaker instance for provider health status
    """

    def __init__(self, memory: MemoryStore, circuit_breaker: CircuitBreaker):
        """
        Initialize the metrics service.

        Args:
            memory: Memory store instance for data persistence
            circuit_breaker: Circuit breaker instance for health monitoring
        """
        self.memory = memory
        self.circuit_breaker = circuit_breaker

    async def record(self, provider_name: str, latency_ms: int, cost: float, success: bool):
        """
        Record metrics for a completed request.

        This method stores request outcome data for analytics and monitoring.
        Metrics are aggregated both globally and per-provider.

        Args:
            provider_name: Name of the provider that handled the request
            latency_ms: Request latency in milliseconds
            cost: Estimated cost of the request in USD
            success: Whether the request succeeded (True) or failed (False)
        """
        await self.memory.record_request_metrics(provider_name, latency_ms, cost, success)

    async def get_global_metrics(self) -> dict:
        """
        Get aggregated metrics across all providers.

        Returns:
            dict: Global metrics including total requests, success rate,
                  average latency, and total cost
        """
        return await self.memory.get_global_metrics()

    async def get_provider_metrics(self) -> dict[str, dict]:
        """
        Get detailed metrics per provider including health status.

        This method combines stored metrics data with current circuit
        breaker status and manual downtime flags to provide a complete
        picture of each provider's health and performance.

        Returns:
            dict: Mapping of provider names to their metrics, including:
                  - requests: Total number of requests
                  - success: Number of successful requests
                  - failures: Number of failed requests
                  - success_rate: Ratio of successful to total requests
                  - avg_latency_ms: Average latency for successful requests
                  - is_down: Manual downtime flag
                  - circuit_status: Current circuit breaker state
        """
        provider_metrics = await self.memory.get_provider_metrics()

        # Enrich metrics with current health status
        for provider_name in provider_metrics.keys():
            state = await self.memory.get_provider_dynamic_state(provider_name)
            provider_metrics[provider_name]["is_down"] = state["is_down"]
            provider_metrics[provider_name]["circuit_status"] = await self.circuit_breaker.get_status(provider_name)

        return provider_metrics
