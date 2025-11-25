"""
Analytics and metrics endpoint routes.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_metrics_service
from app.models import AnalyticsResponse, GlobalMetrics, ProviderMetrics
from app.routing.metrics import MetricsService

router = APIRouter(
    tags=["analytics"],
)


@router.get(
    "/routing/analytics",
    response_model=AnalyticsResponse,
    summary="Get routing analytics",
    description="""
    Get comprehensive routing analytics and performance metrics.
    
    Returns both global and per-provider statistics including:
    
    **Global Metrics:**
    - Total requests across all providers
    - Success and failure counts
    - Overall success rate
    - Average latency (calculated from successful requests only)
    - Total cost incurred
    
    **Per-Provider Metrics:**
    - Request counts and success rates
    - Average latency per provider
    - Current health status (up/down)
    - Circuit breaker state
    
    **Use Cases:**
    - Monitor system health and performance
    - Identify problematic providers
    - Track cost and latency trends
    - Optimize routing strategies
    - Generate usage reports
    """,
)
async def get_analytics(
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> AnalyticsResponse:
    """
    Get comprehensive routing analytics including global and per-provider metrics.

    Returns success rates, latency statistics, and request counts for
    monitoring and optimization purposes.
    """
    global_metrics = await metrics_service.get_global_metrics()
    provider_metrics = await metrics_service.get_provider_metrics()

    return AnalyticsResponse(
        global_metrics=GlobalMetrics(**global_metrics),
        providers={name: ProviderMetrics(**metrics) for name, metrics in provider_metrics.items()},
    )
