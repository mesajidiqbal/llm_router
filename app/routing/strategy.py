import math
from typing import List
from app.config import ProviderSpec
from app.models import UserPreference
from app.routing.classifier import classify
from app.routing.circuit_breaker import CircuitBreaker
from app.storage.memory import MemoryStore


def estimate_cost(provider: ProviderSpec, prompt: str) -> float:
    tokens = math.ceil(len(prompt) / 4)
    cost = tokens * provider.cost_per_token
    return cost


async def select_providers(
    prompt: str,
    preferences: UserPreference,
    providers_list: List[ProviderSpec]
) -> List[ProviderSpec]:
    circuit_breaker = CircuitBreaker()
    memory = MemoryStore()
    
    request_type = classify(prompt)
    
    available_providers = []
    for provider in providers_list:
        state = await memory.get_provider_dynamic_state(provider.name)
        is_down = state["is_down"]
        
        if is_down:
            continue
        
        is_available = await circuit_breaker.is_available(provider.name)
        if not is_available:
            continue
        
        cost = estimate_cost(provider, prompt)
        if preferences.max_cost_per_request is not None and cost > preferences.max_cost_per_request:
            continue
        
        available_providers.append((provider, cost))
    
    def get_score(item):
        provider, cost = item
        score = 0.0
        
        if preferences.priority == "cost":
            score = cost
        elif preferences.priority == "speed":
            score = provider.latency_ms
        elif preferences.priority == "quality":
            score = -provider.quality_score # Negative for descending sort
            
        # Apply boost
        if request_type in provider.specialties:
            if preferences.priority == "quality":
                score *= 1.1 # More negative -> better (10% boost)
            else:
                score *= 0.9 # Lower -> better (10% boost)
                
        return score

    available_providers.sort(key=get_score)
    
    return [p for p, c in available_providers]
