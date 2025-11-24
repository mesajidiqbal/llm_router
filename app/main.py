from dotenv import load_dotenv
import random
load_dotenv()

from fastapi import FastAPI, HTTPException
from typing import List
from app.models import ChatRequest, ChatResponse, ProviderStatus
from app.config import ProviderRegistry
from app.storage.memory import MemoryStore
from app.providers.factory import get_provider
from app.providers.base import RateLimitError
from app.routing.strategy import select_providers
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService


class RouterService:
    def __init__(self):
        self.memory = MemoryStore()
        self.circuit_breaker = CircuitBreaker()
        self.metrics = MetricsService()

    async def handle_request(self, request: ChatRequest) -> ChatResponse:
        if request.user_id:
            user_spend = await self.memory.get_user_spend(request.user_id)
            if user_spend > 1.00:
                raise HTTPException(status_code=402, detail="Budget exceeded")
        
        providers_ordered = await select_providers(
            request.prompt,
            request.preferences,
            ProviderRegistry.providers_list()
        )
        
        if not providers_ordered:
            raise HTTPException(status_code=503, detail="All providers unavailable")
        
        for provider_spec in providers_ordered:
            try:
                provider = get_provider(provider_spec.name)
                resp = await provider.chat(request.prompt, request.preferences.timeout_ms)
                
                await self.circuit_breaker.record_outcome(provider_spec.name, True)
                
                if request.user_id:
                    await self.memory.add_user_spend(request.user_id, resp.cost)
                
                await self.metrics.record(provider_spec.name, resp.latency_ms, resp.cost, True)
                
                return resp
            
            except RateLimitError:
                await self.metrics.record(provider_spec.name, 0, 0, False)
                continue
            
            except Exception:
                await self.circuit_breaker.record_outcome(provider_spec.name, False)
                await self.metrics.record(provider_spec.name, 0, 0, False)
                continue
        
        raise HTTPException(status_code=503, detail="All providers unavailable")


def create_app() -> FastAPI:
    random.seed(42)
    app = FastAPI(title="LLM Routing Service", version="1.0.0")
    router_service = RouterService()
    memory = MemoryStore()
    circuit_breaker = CircuitBreaker()
    metrics_service = MetricsService()

    @app.post("/chat/completions", response_model=ChatResponse)
    async def chat_completions(request: ChatRequest) -> ChatResponse:
        return await router_service.handle_request(request)

    @app.get("/providers", response_model=List[ProviderStatus])
    async def get_providers() -> List[ProviderStatus]:
        providers_dict = ProviderRegistry.providers_dict()
        provider_metrics = await metrics_service.get_provider_metrics()
        
        result = []
        for name, spec in providers_dict.items():
            state = await memory.get_provider_dynamic_state(name)
            circuit_status = await circuit_breaker.get_status(name)
            
            metrics = provider_metrics.get(name, {
                "requests": 0,
                "success": 0,
                "failures": 0,
                "success_rate": 1.0,
                "avg_latency_ms": 0.0,
            })
            
            result.append(ProviderStatus(
                **spec.model_dump(),
                is_down=state["is_down"],
                circuit_status=circuit_status,
                success_rate=metrics["success_rate"],
            ))
        
        return result

    @app.get("/routing/analytics")
    async def get_analytics():
        global_metrics = await metrics_service.get_global_metrics()
        provider_metrics = await metrics_service.get_provider_metrics()
        
        return {
            "global": global_metrics,
            "providers": provider_metrics,
        }

    @app.post("/simulate/failure")
    async def simulate_failure(body: dict):
        provider = body.get("provider")
        down = body.get("down", False)
        
        if not provider:
            raise HTTPException(status_code=400, detail="Provider name required")
        
        provider = provider.lower()
        if provider not in ProviderRegistry.providers_dict():
            raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
        
        await memory.set_provider_down(provider, down)
        
        return {"message": f"Provider {provider} set to down={down}"}

    return app


app = create_app()
