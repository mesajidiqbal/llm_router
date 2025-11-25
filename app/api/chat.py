"""
Chat completion endpoint routes.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_router_service
from app.models import ChatRequest, ChatResponse
from app.services.router_service import RouterService

router = APIRouter(
    tags=["chat"],
    responses={
        402: {"description": "Payment Required - User budget exceeded"},
        503: {"description": "Service Unavailable - All providers failed"},
    },
)


@router.post(
    "/chat/completions",
    response_model=ChatResponse,
    summary="Route chat completion request",
    description="""
    Route a chat completion request to the best available provider.
    
    The system intelligently selects providers based on:
    - User preferences (cost, speed, or quality priority)
    - Prompt classification (code, writing, or analysis)
    - Provider availability and circuit breaker status
    - Budget constraints (per-request and per-user limits)
    - Rate limiting enforcement
    
    If the selected provider fails, the system automatically falls back to
    the next best provider until a successful response is received.
    
    **Budget Enforcement:**
    - Per-request: Respects `max_cost_per_request` preference
    - Per-user: Enforces $1.00 total spending cap when `user_id` is provided
    
    **Error Scenarios:**
    - 402: User has exceeded $1.00 spending limit
    - 503: All providers are unavailable or failed
    """,
)
async def chat_completions(
    request: ChatRequest,
    router_service: RouterService = Depends(get_router_service),
) -> ChatResponse:
    """
    Route a chat completion request to the best available provider.

    Uses intelligent routing based on user preferences, provider availability,
    circuit breaker status, and budget constraints.
    """
    return await router_service.handle_request(request)
