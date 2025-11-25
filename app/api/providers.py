"""
Provider management endpoint routes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.config import ProviderRegistry
from app.dependencies import get_circuit_breaker, get_memory, get_metrics_service
from app.models import FailureSimulationRequest, FailureSimulationResponse, ProviderStatus
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService
from app.storage.memory import MemoryStore

router = APIRouter(
    tags=["providers"],
    responses={
        404: {"description": "Provider not found"},
    },
)


@router.get(
    "/providers",
    response_model=List[ProviderStatus],
    summary="Get provider status",
    description="""
    Get the current status of all configured providers.
    
    Returns comprehensive information including:
    - Provider specifications (model, cost, latency, rate limits)
    - Real-time health status (up/down, circuit breaker state)
    - Performance metrics (success rate, average latency)
    - Specialties and quality scores
    
    **Circuit Breaker States:**
    - CLOSED: Provider is healthy and accepting requests
    - OPEN: Provider is experiencing failures and temporarily blocked
    - HALF_OPEN: Provider is being tested for recovery
    """,
)
async def get_providers(
    memory: MemoryStore = Depends(get_memory),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> List[ProviderStatus]:
    """
    Get the status of all configured providers.

    Returns provider specifications along with real-time status including
    circuit breaker state, success rates, and availability.
    """
    providers_dict = ProviderRegistry.providers_dict()
    provider_metrics = await metrics_service.get_provider_metrics()

    result = []
    for name, spec in providers_dict.items():
        state = await memory.get_provider_dynamic_state(name)
        circuit_status = await circuit_breaker.get_status(name)

        metrics = provider_metrics.get(
            name,
            {
                "requests": 0,
                "success": 0,
                "failures": 0,
                "success_rate": 1.0,
                "avg_latency_ms": 0.0,
            },
        )

        result.append(
            ProviderStatus(
                **spec.model_dump(),
                is_down=state["is_down"],
                circuit_status=circuit_status,
                success_rate=metrics["success_rate"],
            )
        )

    return result


@router.post(
    "/simulate/failure",
    response_model=FailureSimulationResponse,
    summary="Simulate provider failure",
    description="""
    Manually mark a provider as down or up for testing purposes.
    
    This endpoint allows you to simulate provider failures to test:
    - Circuit breaker behavior
    - Automatic failover logic
    - Provider selection strategies
    - Recovery mechanisms
    
    **Use Cases:**
    - Testing circuit breaker transitions (CLOSED → OPEN → HALF_OPEN)
    - Validating automatic fallback to backup providers
    - Demonstrating resilience patterns
    - Load balancing verification
    
    **Note:** This is for testing only. In production, provider health
    is automatically detected through circuit breaker monitoring.
    """,
)
async def simulate_failure(
    request: FailureSimulationRequest,
    memory: MemoryStore = Depends(get_memory),
) -> FailureSimulationResponse:
    """
    Simulate provider failures for testing circuit breaker behavior.

    Set a provider to 'down' state to test failover and recovery mechanisms.
    """
    provider = request.provider.lower()

    if provider not in ProviderRegistry.providers_dict():
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    await memory.set_provider_down(provider, request.down)

    return FailureSimulationResponse(message=f"Provider {provider} set to down={request.down}")
