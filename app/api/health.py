"""
Health check and root endpoint routes.
"""

from fastapi import APIRouter, Depends

from app.config import ProviderRegistry
from app.dependencies import get_circuit_breaker, get_memory
from app.models import HealthResponse, RootResponse
from app.routing.circuit_breaker import CircuitBreaker
from app.storage.memory import MemoryStore

router = APIRouter(
    tags=["health"],
    responses={
        503: {"description": "Service Unavailable - All providers down"},
    },
)


@router.get(
    "/",
    response_model=RootResponse,
    summary="Service information",
    description="Returns basic service information and API documentation links",
)
async def root() -> RootResponse:
    """Root endpoint with service information."""
    return RootResponse(
        message="Welcome to LLM Routing Service",
        version="1.0.0",
        docs={"swagger": "/docs", "redoc": "/redoc"},
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="""
    Check the health of the service and its providers.
    
    Returns 'healthy' if at least one provider is available and operational.
    Returns 'degraded' if all providers are down or unavailable.
    
    Checks both manual downtime status and circuit breaker state for each provider.
    """,
)
async def health(
    memory: MemoryStore = Depends(get_memory),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> HealthResponse:
    """
    Check the health of the service and its providers.
    Returns 'healthy' only if at least one provider is available.
    """
    providers_dict = ProviderRegistry.providers_dict()
    healthy_count = 0
    total_count = len(providers_dict)

    for provider_name in providers_dict.keys():
        state = await memory.get_provider_dynamic_state(provider_name)
        is_available = await circuit_breaker.is_available(provider_name)

        if not state["is_down"] and is_available:
            healthy_count += 1

    status = "healthy" if healthy_count > 0 else "degraded"

    return HealthResponse(
        status=status,
        providers_available=healthy_count,
        providers_total=total_count,
        version="1.0.0",
    )
