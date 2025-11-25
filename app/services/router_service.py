"""
Router Service for orchestrating chat request routing.

This module contains the RouterService class that handles intelligent
provider selection, fallback logic, budget enforcement, and metrics tracking.
"""

import structlog
from fastapi import HTTPException

from app.config import ProviderRegistry, settings
from app.exceptions import RateLimitError, ServiceUnavailableError
from app.models import ChatRequest, ChatResponse
from app.providers.factory import get_provider
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService
from app.routing.strategy import select_providers
from app.storage.memory import MemoryStore

logger = structlog.get_logger()


class RouterService:
    """
    Orchestrates chat request routing with intelligent provider selection.

    This service acts as the central coordinator for handling chat requests by:
    1. Enforcing user budget limits (configurable via settings.user_budget_cap)
    2. Selecting the best provider based on preferences and availability
    3. Implementing automatic fallback to alternative providers on failure
    4. Recording metrics and circuit breaker outcomes
    5. Tracking user spending across requests

    The service uses a circuit breaker pattern to avoid repeatedly calling
    unhealthy providers, and falls back through a ranked list of alternatives
    until a successful response is received or all providers are exhausted.
    """

    def __init__(self, memory: MemoryStore, circuit_breaker: CircuitBreaker, metrics: MetricsService):
        self.memory = memory
        self.circuit_breaker = circuit_breaker
        self.metrics = metrics

    async def handle_request(self, request: ChatRequest) -> ChatResponse:
        """
        Route a chat request to the best available provider.

        Args:
            request: The chat request with prompt and preferences

        Returns:
            ChatResponse from the selected provider

        Raises:
            HTTPException: If budget is exceeded (402)
            ServiceUnavailableError: If no providers are available (503)
        """
        # Step 1: Check user budget before processing (if user_id provided)
        if request.user_id:
            user_spend = await self.memory.get_user_spend(request.user_id)
            if user_spend > settings.user_budget_cap:
                logger.warning("budget_exceeded", user_id=request.user_id, spend=user_spend)
                raise HTTPException(status_code=402, detail="Budget exceeded")

        logger.info("handling_request", prompt_length=len(request.prompt), user_id=request.user_id)

        # Step 2: Get ranked list of providers based on preferences and availability
        # This considers: classification, circuit breaker status, cost constraints, and priority
        providers_ordered = await select_providers(
            request.prompt,
            request.preferences,
            ProviderRegistry.providers_list(),
            self.circuit_breaker,
            self.memory,
        )

        if not providers_ordered:
            logger.error("no_providers_available", reason="empty_list")
            raise ServiceUnavailableError("All providers unavailable")

        # Step 3: Try providers in order until one succeeds (fallback pattern)
        for provider_spec in providers_ordered:
            log = logger.bind(provider=provider_spec.name)
            try:
                log.info("calling_provider")
                provider = get_provider(provider_spec.name)
                resp = await provider.chat(request.prompt, request.preferences.timeout_ms)

                # Success path: Record success, update budget, and return response
                await self.circuit_breaker.record_outcome(provider_spec.name, True)

                if request.user_id:
                    await self.memory.add_user_spend(request.user_id, resp.cost)

                await self.metrics.record(provider_spec.name, resp.latency_ms, resp.cost, True)

                log.info("provider_success", latency_ms=resp.latency_ms, cost=resp.cost)
                return resp

            except RateLimitError:
                # Rate limits are quota issues, not health issues
                # Don't trigger circuit breaker, just try next provider
                log.warning("provider_rate_limited")
                await self.metrics.record(provider_spec.name, 0, 0, False)
                continue

            except Exception as e:
                # Other failures indicate potential provider health issues
                # Record failure in circuit breaker and metrics, then try next provider
                log.error("provider_failed", error=str(e))
                await self.circuit_breaker.record_outcome(provider_spec.name, False)
                await self.metrics.record(provider_spec.name, 0, 0, False)
                continue

        # Step 4: All providers exhausted without success
        logger.error("all_providers_failed")
        raise ServiceUnavailableError("All providers unavailable")
